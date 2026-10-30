import unittest
from sessions import inspect_session,demo_session
from diagnostics import demo_snapshot

class SessionTests(unittest.TestCase):
    def test_unknown_does_not_close_incident(self):
        r=inspect_session([demo_snapshot('line-stale'),{},demo_snapshot('restored')])
        recovered=[e for e in r['events'] if e['kind']=='recovered']
        self.assertEqual(len(recovered),1);self.assertEqual(recovered[0]['frame'],2)
        self.assertEqual(recovered[0]['opened_at'],0)
    def test_stale_repetition_does_not_duplicate_incident(self):
        r=inspect_session([demo_snapshot('line-stale')]*3)
        self.assertEqual(r['summary']['opened'],1);self.assertEqual(r['unresolved'],['line_stale'])
    def test_independent_sensor_must_recover_itself(self):
        d=demo_snapshot('line-stale');d['link_age_ms']=20
        r=inspect_session([d,d]);self.assertEqual(r['summary']['recovered'],0)
    def test_disconnect_then_missing_sensor_not_full_recovery(self):
        d=demo_snapshot('restored');d.pop('line')
        r=inspect_session([demo_snapshot('line-stale'),demo_snapshot('offline'),d])
        self.assertIn('line_stale',r['unresolved']);self.assertNotIn('link_offline',r['unresolved'])
    def test_demo_is_explicit(self):
        r=inspect_session(demo_session(),'demo')
        self.assertEqual(r['summary'],{'frame_count':6,'opened':2,'recovered':2})
        self.assertTrue(all(f['source']=='demo' for f in r['frames']))
    def test_bounds(self):
        for value in ([],{},[{}]*201):
            with self.assertRaises(ValueError):inspect_session(value)

if __name__=='__main__':unittest.main(verbosity=2)
