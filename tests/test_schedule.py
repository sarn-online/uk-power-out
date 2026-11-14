"""Independent exhaustive source-cell and civil-time checks (standard library)."""
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from datetime import date, datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / 'custom_components/power_out'
package = types.ModuleType('reference_engine')
package.__path__ = [str(PKG)]
sys.modules['reference_engine'] = package
from reference_engine.schedule import Scenario, UK, from_settings
from reference_engine.const import LETTERS
TABLES = json.loads((PKG/'schedules.json').read_text())

class ScheduleTests(unittest.TestCase):
    def test_all_cells_and_minutes(self):
        monday = date(2026,11,9)
        for level in range(1,19):
            for r, letter in enumerate(LETTERS):
                s = Scenario(letter,level,monday,monday+timedelta(days=6))
                intervals = s.intervals(TABLES)
                for minute in range(7*1440):
                    now = s.start + timedelta(minutes=minute)
                    local = now.astimezone(UK)
                    rota_day = local.date() - timedelta(days=local.hour == 0 and local.minute < 30)
                    slot = ((local.hour*60+local.minute-30) % 1440)//180
                    expected = TABLES[level-1][r][rota_day.weekday()*8+slot]
                    actual = any(a<=now<b for a,b in intervals)
                    if expected != actual:
                        self.fail((level,letter,now,slot))
                self.assertIsNone(s.evaluate(s.end,intervals)[0])
                self.assertIsNone(s.evaluate(s.start-timedelta(seconds=1),intervals)[0])
                for a,b in zip(intervals,intervals[1:]):
                    self.assertLess(a[1],b[0])

    def test_dst_elapsed_and_wall_clock(self):
        for day,hours in [(date(2026,3,29),2),(date(2026,10,25),4)]:
            s = Scenario('A',1,day,day)
            fake = [[[False]*56 for _ in LETTERS] for _ in range(18)]
            fake[0][0][day.weekday()*8] = True
            a,b = s.intervals(fake)[0]
            self.assertEqual((b-a).total_seconds()/3600,hours)
            self.assertEqual(a.astimezone(UK).hour,0)
            self.assertEqual(b.astimezone(UK).hour,3)

    def test_boundaries_and_continuous_level18(self):
        s = Scenario('U',18,date(2026,12,31),date(2027,1,2))
        intervals = s.intervals(TABLES)
        self.assertEqual(intervals,[(s.start,s.end)])
        self.assertEqual(s.evaluate(s.start,intervals),(True,None,None))
        self.assertIsNone(s.evaluate(s.end,intervals)[0])
        # A transition at exactly now has already happened.
        s = Scenario('A',1,date(2026,11,9),date(2026,11,15))
        intervals=s.intervals(TABLES)
        a,b=intervals[0]
        self.assertTrue(s.evaluate(a,intervals)[0])
        self.assertFalse(s.evaluate(b,intervals)[0])
        self.assertEqual(s.evaluate(a,intervals)[2],b)
        self.assertNotEqual(s.evaluate(a,intervals)[1],a)

    def test_validation(self):
        for letter in 'FIOVZ':
            with self.assertRaises(ValueError): Scenario(letter,1,date.today(),date.today())
        for level in [0,19,True,1.1]:
            with self.assertRaises(ValueError): Scenario('A',level,date.today(),date.today())
        with self.assertRaises(ValueError): Scenario('A',1,date.today(),date.today(),'lldp')
        with self.assertRaises(ValueError): Scenario('A',1,date(2026,2,2),date(2026,2,1))
        with self.assertRaises(ValueError): Scenario('A',1,date(2026,1,1),date(2028,1,1))
        s=Scenario('A',1,date.today(),date.today())
        with self.assertRaises(ValueError): s.evaluate(datetime.now(),[])

    def test_pdf_discrepancy_fixtures(self):
        for level,r,c in [(2,9,38),(2,10,39),(8,3,47),(8,4,47),(12,12,45),(17,6,51)]:
            self.assertTrue(TABLES[level-1][r][c])

if __name__ == '__main__': unittest.main()
