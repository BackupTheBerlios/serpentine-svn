# Copyright (C) 2004 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Library General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
# Authors: Tiago Cogumbreiro <cogumbreiro@users.sf.net>

"""
Contains three groups of classes. Events, listeners and operations.

The Operation is used in the OperationsQueue, which is an Operation itself, to
process other operations in a sequenced way. They use gobject's main loop.
"""

import gobject
#TODO: listeners must be grouped by class
#

class OperationListener (object):
    def on_finished (self, event):
        pass

SUCCESSFUL = 0
ABORTED = 1
ERROR = 2

class Event (object):
    def __init__ (self, source):
        self.source = source
    
class FinishedEvent (Event):
    def __init__ (self, source, id):
        Event.__init__ (self, source)
        self.id = id

class Listenable (object):
    def __init__ (self):
        self.__listeners = []
        
    listeners = property (\
            fget = lambda self: self.__listeners,
            doc  = "The list of available listeners.")

class Operation (Listenable):
    """
    An operation is run assynchrounously. It is a Listenable and as such
    classes which extend this one should call the event on_finished of it's
    listeners when this operation is finished.
    """
    
    title = None
    description = None
    
    can_start = property (lambda self: not self.running, doc = "Checks if the operation can start. By default you can start an operation when it's not running.")
    can_stop = property (lambda self: self.running, doc = "Checks if this operation can stop. By default you can stop operations that are running.")
    running = property (doc = "Tests if the operation is running.")

    def start (self):
        pass
    
    def stop (self):
        pass

    def _send_finished_event (self, status):
        """Broadcasts to all listeners the finished event. Simplifies the 
        task of creating the event and iterating over listeners."""
        e = FinishedEvent (self, status)
        for l in self.listeners:
            if hasattr (l, "on_finished"):
                l.on_finished (e)

class CallableOperation (Operation):
    """Simple operations that takes a callable object (ie: function) and creates
    an non-measurable Operation."""
    
    can_start = property (lambda: True)
    can_stop = property (lambda: False)
    running = property (lambda: False)
    
    def __init__ (self, callable):
        self.callable = callable
        Operation.__init__ (self)
    
    def start (self):
        self.callable ()
        self._send_finished_event (SUCCESSFUL)

try:
    import subprocess, os
    
    class SubprocessOperation (Operation):    
        def __init__ (self, *args, **kwargs):
            super (SubprocessOperation, self).__init__ ()
            self.args = args
            self.kwargs = kwargs
        
        pid = property (lambda self: self.__pid)
        
        can_start = property (lambda self: self.pid is not None)
    
        can_stop = property (lambda self: self.pid is not None)
    
        running = property (lambda self: self.pid is not None)
        
        def start (self):
            try:
                proc = subprocess.Popen (*self.args, **self.kwargs)
                self.__pid = proc.pid
                self.__id = gobject.child_watch_add (self.pid, self.__on_finish)
            except Exception, e:
                print "Error:", e
        
        def stop (self):
            try:
                os.kill (self.pid, 9)
            except OSError:
                pass
        
        def __on_finish (self, pid, status):
            self._send_finished_event (status == 0 and SUCCESSFUL or ERROR)
            self.__pid = None
except ImportError:
    pass        
    
class MeasurableOperation (Operation):
    progress = property (doc = "Returns the operation's progress.")

class OperationsQueueListener (OperationListener):
    def before_operation_starts (self, event, operation):
        pass
    
class OperationsQueue (MeasurableOperation, OperationListener):
    """
    Operation Queuees allow a user to enqueue a number of operations and run
    them sequentially.
    If one of the operations is aborted or has an error the whole queue is 
    aborted or returns an error too. The error returned is the same returned
    by the problematic operation. All the elements remaining on the queue are
    removed.
    """
    
    def __init__ (self, operations = None):
        Operation.__init__ (self)
        
        if operations is None:
            operations = []
            
        self.__operations = operations
        self.__done = 0
        self.__curr_oper = None
        self.__progress = 0.0
        self.__total = 0
        self.__abort_on_failure = True
    
    def __is_running (self):
        return self.__curr_oper != None
        
    running = property (__is_running)
    
    def __get_progress (self):
        if not self.running:
            # Return 1 if there are no operations pending
            # and we are not running and there are operations done
            # else return 0
            return (len(self.__operations) == 0 and self.__done and 1.0) or 0.0
        # All that were done, the ones remaining plus the current working operation
        total = self.__total
        partial = 0.0
        if isinstance(self.__curr_oper, MeasurableOperation):
            partial = self.__curr_oper.progress
        return (self.__done + partial) / total
        
    progress = property (__get_progress)
    
    def __set_abort_on_failure (self, val):
        assert isinstance (val, bool)
        self.__abort_on_failure = val
    
    abort_on_failure = property (lambda self: self.__abort_on_failure,
                                 __set_abort_on_failure,
                                 doc = "If one operation stops abort progress and propagate event.")
        
    def start (self):
        """
        Starts all the operations on queue, sequentially.
        """
        assert not self.running, self.__curr_oper
        self.__done = 0
        self.__total = len (self.__operations)
        self.__progress = 0.0
        self.__started = True
        gobject.idle_add (self.__start_next)
    
    def append (self, oper):
        self.__operations.append (oper)
    
    def insert (self, index, oper):
        self.__operations.insert (index, oper)
        
    # Private methods:
    def __start_next (self):
        if len (self.__operations):
            oper = self.__operations[0]
            del self.__operations[0]
            e = Event (self)
            for l in self.listeners:
                if hasattr (l, "before_operation_starts"):
                    l.before_operation_starts (e, oper)
                
            oper.listeners.append (self)
            self.__curr_oper = oper
            oper.start()
            
        else:
            self.__started = False
            e = FinishedEvent (self, SUCCESSFUL)
            for l in self.listeners:
                if hasattr (l, "on_finished"):
                    l.on_finished (e)
    
    
    
    def on_finished (self, evt):
        assert isinstance (evt, FinishedEvent), evt
        # Remove the listener connection
        evt.source.listeners.remove (self)
        # One more done
        self.__done += 1
        self.__curr_oper = None
        
        # Abort on not success
        if self.abort_on_failure and evt.id != SUCCESSFUL:
            # Clear remaining operations
            self.__operations = []
            evt.source = self
            for l in self.listeners:
                l.on_finished (evt)
        else:
            # Start next operation
            self.__start_next()
    
    can_stop = property (lambda self: self.running and self.__curr_oper.can_stop)
    
    def stop (self):
        assert self.can_stop, "Check if the operation can be stopped first."
        self.__curr_oper.stop ()
    
    __len__ = lambda self: len (self.__operations)
    
    def __repr__ (self):
        return "{%s: %s}" % (
            super(OperationsQueue, self).__repr__(),
            self.__operations.__repr__()
        )
    
class MapFunctor (object):
    def __init__ (self, funcs):
        self.__funcs = funcs
        
    def __call__ (self, *args, **keyws):
        r = []
        for f in self.__funcs:
            r.append (f(*args, **keyws))
        return tuple (r)

class MapProxy (object):
    """
    This class acts as a hub or a proxy for calling methods on multiple objects.
    The method called from an instance of this class will be transparently
    called in all elements contained in this instance. The added elements is of
    a dictionary type and can be accessed by the __getitem__ and __setitem__ of
    this instance.
    """
    def __init__ (self, elements):
        self.__elements = elements
    
    def __getattr__ (self, attr):
        funcs = []
        for key in self.__elements:
            funcs.append (getattr (self.__elements[key], attr))
        
        return MapFunctor (funcs)
    
    def __getitem__ (self, key):
        return self.__elements[key]
    
    def __setitem__ (self, key, value):
        self.__elements[key] = value
    
    def __delitem__ (self, key):
        del self.__elements[key]
    
    def has_key (self, key):
        return self.__elements.has_key (key)

if __name__ == '__main__':
    import sys, gtk
    class Listener:
        def on_finished (self, evt):
            gtk.main_quit ()
            
    oper = SubprocessOperation (sys.argv[1:])
    oper.listeners.append (Listener())
    oper.start ()
    gtk.main ()
    