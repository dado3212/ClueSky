import unittest
from main import extract_chunks

class TestMyFunction(unittest.TestCase):
  def test_basic(self):
    cleaned = 'kenmartinbskysocial Do we have a with ourselves plan yet  Im humbly asking because up here in PA its looking like were still running around like chickens with our heads cut off  Please tell me theres a plan other than constantly begging us for money '
    self.assertSetEqual(set(extract_chunks('h our', cleaned, 15 + 4 - 1).values()), set(['with ourselves plan', 'with ourselves', 'have a with ourselves', 'with our', 'a with ourselves', 'chickens with our', 'with our heads cut', 'a with ourselves plan', 'with our heads']))
    
  def test_trailing_space(self):
    cleaned = 'kenmartinbskysocial Do we have a with ourselves plan yet  Im humbly asking because up here in PA its looking like were still running around like chickens with our heads cut off  Please tell me theres a plan other than constantly begging us for money '
    self.assertSetEqual(set(extract_chunks('h our ', cleaned, 15 + 4 - 1).values()), set(['with our', 'chickens with our', 'with our heads cut off', 'with our heads cut', 'with our heads']))

  def test_multiline(self):
    cleaned = '''
    NDP strategist George Soule says in our postdebate analysis panel that a decent growth for the NDP is being seen in specific regions in contrast to what the national vote numbers are currently showing Watch our special coverage youtubecomliveZHWGSMfPlk
'''
    self.assertSetEqual(set(extract_chunks('h our ', cleaned, 15 + 4 - 1).values()), set(['Watch our', 'Watch our special', 'showing Watch our']))

if __name__ == '__main__':
  unittest.main()