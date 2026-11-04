import unittest
from modal_admission import admit

class Admission(unittest.TestCase):
 def test_boundary_and_monthly_cap(self):
  state=None
  for n in range(20):state=admit(state,'2026-11','28.75','0',str(n),'fixture-hash',1)
  self.assertEqual(sum(r['reserved_usd'] for r in state['jobs'].values()),5)
  with self.assertRaisesRegex(ValueError,'cap is reached'):admit(state,'2026-11',0,0,'twenty-first','fixture-hash',1)
  next_month=admit(state,'2026-12',0,0,'new-job','fixture-hash',1)
  self.assertEqual(len(next_month['jobs']),1);self.assertEqual(len(state['jobs']),20)
 def test_metering_failures_never_admit(self):
  for metered,billed in [('28.751','0'),('0','.001'),('NaN','0'),('0','NaN'),('-1','0'),('invalid','0')]:
   with self.assertRaises(ValueError):admit(None,'2026-11',metered,billed,'fixture','hash',1)
 def test_duplicate_job_does_not_mutate_admission(self):
  state=admit(None,'2026-11',0,0,'same','hash',1)
  with self.assertRaisesRegex(ValueError,'already admitted'):admit(state,'2026-11',0,0,'same','hash',2)
  self.assertEqual(state['jobs']['same']['at'],1)
 def test_new_owner_credit_is_never_assumed_and_custom_cap_is_honored(self):
  with self.assertRaises(ValueError):admit(None,'2026-11',0,0,'fixture','hash',1,credit_ceiling_usd=0)
  state=admit(None,'2026-11',0,0,'first','hash',1,limit_usd=.25,credit_ceiling_usd=10)
  with self.assertRaisesRegex(ValueError,'cap is reached'):admit(state,'2026-11',0,0,'second','hash',1,limit_usd=.25,credit_ceiling_usd=10)

if __name__=='__main__':unittest.main()
