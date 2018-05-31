#!/usr/bin/env python

import sys
import os
import argparse
import random
import unittest

plugin_directory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(plugin_directory)

import rainbow_utils


class TestStatuslineGeneration(unittest.TestCase):
    def test_run1(self):
        # 10,a,b,20000,5
        # a1 a2 a3 a4  a5
        test_stln = rainbow_utils.generate_tab_statusline(1, ['10', 'a', 'b', '20000', '5'])
        test_stln_str = ''.join(test_stln)
        canonic_stln = 'a1 a2 a3 a4  a5'
        self.assertEqual(test_stln_str, canonic_stln)

    def test_run2(self):
        # 10  a   b   20000   5
        # a1  a2  a3  a4      a5
        test_stln = rainbow_utils.generate_tab_statusline(4, ['10', 'a', 'b', '20000', '5'])
        test_stln_str = ''.join(test_stln)
        canonic_stln = 'a1  a2  a3  a4      a5'
        self.assertEqual(test_stln_str, canonic_stln)

    def test_run3(self):
        # 10  a   b   20000   5
        # a1  a2
        test_stln = rainbow_utils.generate_tab_statusline(4, ['10', 'a', 'b', '20000', '5'], 9)
        test_stln_str = ''.join(test_stln)
        canonic_stln = 'a1  a2'
        self.assertEqual(test_stln_str, canonic_stln)


    def test_run4(self):
        # 10  a   b   20000   5
        # a1  a2  a3
        test_stln = rainbow_utils.generate_tab_statusline(4, ['10', 'a', 'b', '20000', '5'], 10)
        test_stln_str = ''.join(test_stln)
        canonic_stln = 'a1  a2  a3'
        self.assertEqual(test_stln_str, canonic_stln)
