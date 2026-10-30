"""Local diagnostic viewer: only GET /api/status is sent to the existing backend."""
import argparse,json,os
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import Request,build_opener,HTTPRedirectHandler
from diagnostics import diagnose,answer,demo_snapshot
from sessions import inspect_session,demo_session

HERE=Path(__file__).resolve().parent
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def read_live(runtime):
    config=json.loads(runtime.read_text(encoding='utf-8-sig'))
    if config.get('demo') is True: raise ValueError('该接口是演示服务')
    u=urlsplit(config['url'])
    if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost') or u.username or u.password or u.query or u.fragment:
        raise ValueError('仅允许本机原调试服务')
    req=Request(config['url'].rstrip('/')+'/api/status',method='GET')
    with build_opener(NoRedirect).open(req,timeout=3) as r:
        raw=r.read(1024*1024+1)
    if len(raw)>1024*1024: raise ValueError('状态响应过大')
    data=json.loads(raw)
    if isinstance(data,dict) and (data.get('demo') is True or data.get('simulation') is True or 'SIMULAT' in str(data.get('mode','')).upper()):
        raise ValueError('示例服务不能作为真实接口')
    return data

def make_handler(runtime):
    class Handler(BaseHTTPRequestHandler):
        def send(self,status,body,kind='application/json; charset=utf-8'):
            if not isinstance(body,bytes): body=json.dumps(body,ensure_ascii=False).encode('utf-8')
            self.send_response(status);self.send_header('Content-Type',kind)
            self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(body)
        def host_ok(self):
            return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def do_GET(self):
            if not self.host_ok(): return self.send(403,{'error':'请使用本机地址'})
            p=urlsplit(self.path).path
            if p in ('/','/walkthrough'): self.send(200,(HERE/('index.html' if p=='/' else 'walkthrough.html')).read_bytes(),'text/html; charset=utf-8')
            elif p in ('/app.js','/style.css','/walkthrough.js'):
                self.send(200,(HERE/p[1:]).read_bytes(),'text/javascript; charset=utf-8' if p.endswith('.js') else 'text/css; charset=utf-8')
            elif p=='/api/health': self.send(200,dict(ok=True,read_only=True,version='0.2'))
            else: self.send(404,{'error':'没有这个接口'})
        def do_POST(self):
            if not self.host_ok() or self.headers.get('Origin')!='http://'+self.headers.get('Host',''):
                return self.send(403,{'error':'请在本机页面操作'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.send(415,{'error':'需要JSON请求'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1024*1024: raise ValueError('请求过大或为空')
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict): raise ValueError('请求应为对象')
                p=urlsplit(self.path).path
                if p=='/api/session':
                    mode=body.get('mode')
                    if mode=='demo': result=inspect_session(demo_session(),'demo')
                    elif mode=='import': result=inspect_session(body.get('snapshots'),'import')
                    else: raise ValueError('回放来源无效')
                    return self.send(200,result)
                if p=='/api/demo': report=diagnose(demo_snapshot(body.get('scenario')),'demo')
                elif p=='/api/live':
                    try: report=diagnose(read_live(runtime),'live')
                    except (OSError,ValueError,KeyError,TypeError):
                        return self.send(503,{'error':'本机原调试服务未读通。先恢复原服务，或导入其状态JSON；本次没有取得实车快照。'})
                elif p=='/api/analyze': report=diagnose(body.get('snapshot'),'import')
                elif p=='/api/ask':
                    # Recompute from the snapshot, never trust client-provided conclusions.
                    mode=body.get('mode')
                    if mode=='demo': report=diagnose(demo_snapshot(body.get('scenario')),'demo')
                    elif mode=='live':
                        try: report=diagnose(read_live(runtime),'live')
                        except (OSError,ValueError,KeyError,TypeError): return self.send(503,{'error':'真实接口本次未读通，不能沿用旧快照回答。'})
                    elif mode=='import': report=diagnose(body.get('snapshot'),'import')
                    else: raise ValueError('请先取得一份状态快照')
                    return self.send(200,dict(answer=answer(report,body.get('question')),report=report))
                else: return self.send(404,{'error':'仅提供诊断接口'})
                self.send(200,report)
            except (ValueError,TypeError,OverflowError): self.send(400,{'error':'请求或状态格式不正确，请检查JSON内容。'})
        def log_message(self,*args): pass
    return Handler

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8788)
    parser.add_argument('--open',action='store_true',help='服务端口就绪后打开浏览器')
    parser.add_argument('--runtime',type=Path,default=HERE/'runtime.json')
    args=parser.parse_args()
    try:
        server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(args.runtime))
    except OSError:
        if not args.open: raise
        try:
            with build_opener(NoRedirect).open(f'http://127.0.0.1:{args.port}/api/health',timeout=2) as r:
                health=json.load(r)
            if health.get('read_only') is not True or health.get('version')!='0.2': raise ValueError('端口被其他服务占用')
        except (OSError,ValueError): raise SystemExit('端口被占用，请通过 --port 选择其他端口。')
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{args.port}/')
        raise SystemExit(0)
    server.daemon_threads=True
    print(f'小车调试助手 http://127.0.0.1:{server.server_port}/',flush=True)
    if args.open:
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{server.server_port}/')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
