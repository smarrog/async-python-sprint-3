import unittest

from utils import MaxSizeList


class MaxSizeListTestCase(unittest.TestCase):
    def test_add_to_limited(self):
        max_size_list: MaxSizeList = MaxSizeList(2)

        max_size_list.add(10)

        self.assertEqual(1, len(max_size_list.data))
        self.assertEqual(10, max_size_list.data[0])

        max_size_list.add(20)

        self.assertEqual(2, len(max_size_list.data))
        self.assertEqual(10, max_size_list.data[0])
        self.assertEqual(20, max_size_list.data[1])

        max_size_list.add(30)

        self.assertEqual(2, len(max_size_list.data))
        self.assertEqual(20, max_size_list.data[0])
        self.assertEqual(30, max_size_list.data[1])

    def test_add_to_unlimited(self):
        max_size_list: MaxSizeList = MaxSizeList(0)

        max_size_list.add(5)

        self.assertEqual(1, len(max_size_list.data))
        self.assertEqual(5, max_size_list.data[0])
