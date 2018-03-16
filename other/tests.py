#!/usr/bin/env python

import sys
import os
import argparse
import random
import unittest

plugin_directory = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(plugin_directory)

import rainbow_utils


class TestHeaderGuessing(unittest.TestCase):
    def test_run1(self):
        header = ['name', 'age']
        sampled_entries = [['Dima', '29'], ['Alice', '1.5'], ['future generation', '-20']]
        is_header = rainbow_utils.guess_if_header(header, sampled_entries)
        self.assertTrue(is_header)


    def test_run2(self):
        header = ['name', 'age']
        sampled_entries = [['Dima', 'twenty nine'], ['Alice', 'one']]
        is_header = rainbow_utils.guess_if_header(header, sampled_entries)
        self.assertTrue(not is_header)


    def test_run3(self):
        header = ['type', 'story']
        sampled_entries = [['fairytale', 'Once upon a time there was a beautiful girl who lived...'], ['romance', 'She looked outside her window and saw an approaching ship']]
        is_header = rainbow_utils.guess_if_header(header, sampled_entries)
        self.assertTrue(not is_header)


    def test_run4(self):
        header = ['type', 'story']
        sampled_entries = [['fairytale', 'Once upon a time there was a beautiful girl who lived...'], ['romance', 'She looked outside her window and saw an approaching ship'], ['none', 'none'], ['', '']]
        is_header = rainbow_utils.guess_if_header(header, sampled_entries)
        self.assertTrue(not is_header)


    def test_run5(self):
        header = ['name', 'age']
        sampled_entries = [['Dima', '29'], ['Alice', '1.5'], ['29', 'Liuba']]
        is_header = rainbow_utils.guess_if_header(header, sampled_entries)
        self.assertTrue(not is_header);


    def test_run6(self):
        header = ['"name"', '"age"']
        sampled_entries = [['Dima', '29.0'], ['Alice', '1.5'], ['future generation', '-20.0']]
        is_header = rainbow_utils.guess_if_header(header, sampled_entries)
        self.assertTrue(is_header)


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
