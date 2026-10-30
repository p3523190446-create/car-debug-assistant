import copy,json,tempfile,threading,unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from diagnostics import diagnose,answer,demo_snapshot
from app import make_handler,read_live

class DiagnosisTests(unittest.TestCase):
    def codes(self,d): return {x['code'] for x in diagnose(d)['findings']}
    def test_fresh_link_does_not_refresh_sensor(self):
        d=demo_snapshot('line-stale');self.assertIn('link_ok',self.codes(d));self.assertIn('line_stale',self.codes(d))
    def test_recovery_requires_sensor_fields(self):
        d=demo_snapshot('restored');self.assertEqual(diagnose(d)['status'],'checked')
        d.pop('line');self.assertEqual(diagnose(d)['status'],'unknown');self.assertNotIn('line_ok',self.codes(d))
    def test_offline_ignores_old_good_sensor(self):
        d=demo_snapshot('offline');self.assertIn('line_unknown',self.codes(d));self.assertNotIn('line_ok',self.codes(d))
    def test_age_boundaries(self):
        for age,expected in [(1499,'line_ok'),(1500,'line_stale'),(-1,'line_invalid'),(None,'line_invalid'),(True,'line_invalid'),(float('nan'),'line_invalid')]:
            with self.subTest(age=age):
                d=demo_snapshot('restored');d['line']['age_ms']=age;self.assertIn(expected,self.codes(d))
    def test_link_boundary_and_types(self):
        for age,expected in [(2999,'link_ok'),(3000,'link_stale'),(-1,'link_unknown'),(None,'link_unknown'),(True,'link_unknown')]:
            with self.subTest(age=age):
                d=demo_snapshot('restored');d['link_age_ms']=age;self.assertIn(expected,self.codes(d))
    def test_invalid_samples_are_not_healthy(self):
        for raw,mask in [([1]*7,0),([True]*8,0),([65536]*8,0),([1]*8,256),([1]*8,True)]:
            d=demo_snapshot('restored');d['line'].update(raw=raw,digital_mask=mask);self.assertIn('line_invalid',self.codes(d))
    def test_capability_not_motion_permission(self):
        r=diagnose(demo_snapshot('capability'));self.assertEqual(r['issue_codes'],[])
        self.assertEqual(r['status'],'notice');self.assertIn('未开放',r['title'])
        f=next(x for x in r['findings'] if x['code']=='drive_unavailable');self.assertIn('不能将它等同',f['explanation'])
    def test_missing_caps_not_denied(self):
        d=demo_snapshot('restored');d.pop('capabilities');self.assertIn('drive_unknown',self.codes(d));self.assertNotIn('drive_unavailable',self.codes(d))
    def test_input_is_unchanged(self):
        d=demo_snapshot('restored');saved=copy.deepcopy(d);diagnose(d);self.assertEqual(d,saved)
    def test_source_and_unknown_questions(self):
        for source in ('demo','live','import'): self.assertEqual(diagnose({},source)['source'],source)
        r=diagnose(demo_snapshot('line-stale'));self.assertIn('line.age_ms',answer(r,'巡线怎么了'))
        self.assertIn('无法从现有字段判断',answer(r,'天气怎么样'))

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.runtime=Path(cls.tmp.name)/'runtime.json'
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(cls.runtime))
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls): cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
    def request(self,path,body,origin=True):
        headers={'Content-Type':'application/json'}
        if origin: headers['Origin']=self.base
        return urlopen(Request(self.base+path,data=json.dumps(body).encode(),headers=headers),timeout=4)
    def test_demo_and_ask(self):
        with self.request('/api/demo',{'scenario':'line-stale'}) as r: self.assertIn('line_stale',json.load(r)['issue_codes'])
        with self.request('/api/ask',{'mode':'demo','scenario':'line-stale','question':'巡线怎么了'}) as r: self.assertIn('4600',json.load(r)['answer'])
    def test_import_not_live(self):
        with self.request('/api/analyze',{'snapshot':demo_snapshot('restored')}) as r: self.assertEqual(json.load(r)['source'],'import')
    def test_live_unavailable_returns_no_report(self):
        with self.assertRaises(HTTPError) as cm: self.request('/api/live',{})
        self.assertEqual(cm.exception.code,503);self.assertNotIn('findings',json.load(cm.exception))
    def test_cross_origin_denied(self):
        with self.assertRaises(HTTPError) as cm:self.request('/api/demo',{'scenario':'restored'},False)
        self.assertEqual(cm.exception.code,403)
    def test_no_control_route(self):
        with self.assertRaises(HTTPError) as cm:self.request('/api/drive/start',{})
        self.assertEqual(cm.exception.code,404)
    def test_unknown_fields_fail_closed(self):
        with self.request('/api/analyze',{'snapshot':{}}) as r:self.assertEqual(json.load(r)['status'],'unknown')
    def test_import_session_source_and_recovery(self):
        snapshots=[demo_snapshot('line-stale'),{},demo_snapshot('restored')]
        with self.request('/api/session',{'mode':'import','snapshots':snapshots}) as r:
            result=json.load(r)
        self.assertEqual(result['source'],'import');self.assertEqual(result['summary']['recovered'],1)
        self.assertEqual(result['events'][-1]['frame'],2)
    def test_session_does_not_accept_fake_live_source(self):
        with self.assertRaises(HTTPError) as cm:self.request('/api/session',{'mode':'live','snapshots':[{}]})
        self.assertEqual(cm.exception.code,400)
    def test_only_get_sent_to_backend(self):
        calls=[]
        class Stub(BaseHTTPRequestHandler):
            def do_GET(self):
                calls.append((self.command,self.path));b=json.dumps(demo_snapshot('restored')).encode()
                self.send_response(200);self.end_headers();self.wfile.write(b)
            def log_message(self,*a):pass
        s=ThreadingHTTPServer(('127.0.0.1',0),Stub);threading.Thread(target=s.serve_forever,daemon=True).start()
        try:
            self.runtime.write_text(json.dumps({'url':f'http://127.0.0.1:{s.server_port}/existing'}),encoding='utf-8')
            with self.request('/api/live',{}) as r:self.assertEqual(json.load(r)['source'],'live')
            self.assertEqual(calls,[('GET','/existing/api/status')])
        finally:
            s.shutdown();s.server_close();self.runtime.unlink()
    def test_remote_or_demo_runtime_rejected(self):
        for config in [{'url':'https://example.com/'},{'url':'http://127.0.0.1/','demo':True}]:
            self.runtime.write_text(json.dumps(config),encoding='utf-8')
            with self.assertRaises(ValueError):read_live(self.runtime)
        self.runtime.unlink()

if __name__=='__main__':unittest.main(verbosity=2)
