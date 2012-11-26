from unittest import TestCase

from buildergen import MakefileBuilder

class TestMakefileBuilderCommentMethods(TestCase):
    @classmethod
    def setUp(self):
        self.m = MakefileBuilder()
        self.content = 'the md5 is ab98a7b91094a4ebd9fc0e1a93e985d6'
        self.output = ['\t@echo ' + self.content ]

    def test_msg_meth(self):
        b = 'msg1'
        self.m.msg(self.content, block=b)

        self.assertEqual(self.output, self.m.get_block(b))

    def test_message_meth(self):
        b = 'message1'
        self.m.message(self.content, block=b)

        self.assertEqual(self.output, self.m.get_block(b))

    def test_message_interface(self):
        self.m.message(self.content, block='message1')
        self.m.msg(self.content, block='msg1')

        self.assertIsNot(self.m.get_block('message1'), self.m.get_block('msg1'))
        self.assertEqual(self.m.get_block('message1'), self.m.get_block('msg1'))
        self.assertEqual(self.m.get_block('msg1') + self.m.get_block('message1'), self.m.builder['_all'])


class TestMakefileBuilderVariableMethods(TestCase):
    @classmethod
    def setUp(self):
        self.m = MakefileBuilder()
        self.variable = 'var'
        self.value0 = '$(makepathvar)/build/$(branch)/'
        self.value1 = '$(makepathvar)/archive/$(branch)/'
        self.value2 = 'bin lib opt srv local usr src'

    def test_var_meth1(self):
        b = 'var1'
        v = self.value1

        self.m.var(self.variable, v, block=b)
        self.assertEqual(self.m.get_block(b)[0], self.variable + ' = ' + v)

    def test_var_meth2(self):
        b = 'var2'
        v = self.value2

        self.m.var(self.variable, v, block=b)
        self.assertEqual(self.m.get_block(b)[0], self.variable + ' = ' + v)

    def test_var_meth3(self):
        b = 'var3'
        v = self.value2

        self.m.var(self.variable, v, block=b)
        self.assertEqual(self.m.get_block(b)[0], self.variable + ' = ' + v)

    def test_append_var_meth1(self):
        b = 'append_var1'
        v = self.value1

        self.m.append_var(self.variable, v, block=b)
        self.assertEqual(self.m.get_block(b)[0], self.variable + ' += ' + v)

    def test_var_meth2(self):
        b = 'append_var2'
        v = self.value2

        self.m.append_var(self.variable, v, block=b)
        self.assertEqual(self.m.get_block(b)[0], self.variable + ' += ' + v)

    def test_var_meth3(self):
        b = 'append_var3'
        v = self.value2

        self.m.append_var(self.variable, v, block=b)
        self.assertEqual(self.m.get_block(b)[0], self.variable + ' += ' + v)
