from common import *

import unittest, os.path, tempfile, os

class SafeFileWriteTest (unittest.TestCase):
    def testAbort (self):
        exists = os.path.exists ("test1")
        fd = SafeFileWrite ("test1")
        fd.write ("foo")
        fd.abort ()
        self.assertEqual (os.path.exists("test1"), exists)
    
    def testAbort2 (self):
        fd, filename = tempfile.mkstemp ()
        os.close (fd)
        
        original_data = "Hello world!"
        new_data = "Goodbye world!"
        
        # Write the contents of the file
        fd = open (filename, "w")
        fd.write (original_data)
        fd.close ()
        
        # Now create a file and abort it
        fd = SafeFileWrite (filename)
        fd.write (new_data)
        fd.abort ()
        
        fd = open (filename)
        buff = fd.read ()
        fd.close ()
        
        self.assertEqual (buff, original_data)
    
    def testDataWritten (self):
        fd, filename = tempfile.mkstemp ()
        os.close (fd)
        
        original_data = "Hello world!"
        new_data = "Goodbye world!"
        
        # Write the contents of the file
        fd = open (filename, "w")
        fd.write (original_data)
        fd.close ()
        
        # Now create a file and abort it
        fd = SafeFileWrite (filename)
        fd.write (new_data)
        fd.close ()
        
        fd = open (filename)
        buff = fd.read ()
        fd.close ()
        
        self.assertEqual (buff, new_data)
    
    def testNewFile (self):
        filename = "fjsdafjsd123"
        self.assertFalse (os.path.exists (filename))

        new_data = "Goodbye world!"
        
        # Now create a file and abort it
        fd = SafeFileWrite (filename)
        fd.write (new_data)
        fd.close ()
        
        fd = open (filename)
        buff = fd.read ()
        fd.close ()
        
        self.assertEqual (buff, new_data)
        
        self.assertTrue (os.path.exists (filename))
        
        os.unlink (filename)
        

    
if __name__ == '__main__':
    unittest.main ()