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
    def __init__ (self, source, id, error = None):
        Event.__init__ (self, source)
        self.id = id
        self.error = error

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

    def _notify (self, method_name, *args, **kw):
        [getattr(listener, method_name)(*args, **kw) \
            for listener in self.listeners if hasattr(listener, method_name)]

    def _send_finished_event (self, status, error=None, source=None):
        """
        Broadcasts to all listeners the finished event. Simplifies the 
        task of creating the event and iterating over listeners.
        """
        
        if source is None:
            source = self
            
        evt = FinishedEvent(source, status, error)
        self._notify("on_finished", evt)
                
                
    def _propagate (self, evt, source = None):
        self._send_finished_event (evt.id, evt.error, source)



class FailledOperation(Operation):
    def __init__(self, error=None, source=None):
        if source is None:
            source = self
            
        self.error = error
        self.source = source
        
        super(FailledOperation, self).__init__()
    
    def start(self):
        self._send_finished_event(ERROR, self.error, self.source)
        
    
    can_start = property(lambda: True)
    can_stop = property (lambda: False)
    running = property (lambda: False)



def operation_factory(func):
    """
    This decorator protects operation factories (functions wich return
    operators by wrapping a try catch, if the function, by any chance, raises
    an exception a FailledOperation is returned instead.
    """
    
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception, err:
            return FailledOperation(error=err)

    return wrapper
    
    
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
    import subprocess
    import os
    
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
            if status == 0:
                status = SUCCESSFUL
            else:
                status = ERROR
                
            self._send_finished_event(status)
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
        self._stop_now = False
    
    def _call_later(self, callable):
        gobject.idle_add(callable)
    
    def __is_running (self):
        return self.__curr_oper != None
        
    running = property (__is_running)
    
    def __get_progress (self):
        if not self.running:
            # Return 1 if there are no operations pending
            # and we are not running and there are operations done
            # else return 0
            if len(self.__operations) == 0 and self.__done:
                return 1.0
            else:
                return 0.0
        # All that were done, the ones remaining plus the current working operation
        total = self.__total
        partial = 0.0
        if isinstance(self.__curr_oper, MeasurableOperation):
            partial = self.__curr_oper.progress
            assert partial is not None, (self.__curr_oper, self.__curr_oper.progress)
        return (self.__done + partial) / total
        
    progress = property (__get_progress)
    
    def __set_abort_on_failure (self, val):
        assert isinstance (val, bool)
        self.__abort_on_failure = val
    
    abort_on_failure = property (lambda self: self.__abort_on_failure,
                                 __set_abort_on_failure,
                                 doc = "If one operation stops abort progress and propagate event.")

    def start(self):
        """
        Starts all the operations on queue, sequentially.
        """
        assert not self.running, self.__curr_oper

        self._stop_now = False
        self.paused = False
        self.__done = 0
        self.__total = len(self.__operations)
        self.__progress = 0.0
        self.__started = True
        self.paused = False
        self._call_later(self.__start_next)
    
    def append (self, oper):
        self.__operations.append (oper)
    
    def insert (self, index, oper):
        self.__operations.insert (index, oper)
        
    # Private methods:
    def __start_next (self):
        if len(self.__operations) and not self.paused:
            oper = self.__operations.pop(0)
            
            self._notify("before_operation_starts", Event(self), oper)
            self.__curr_oper = oper

            oper.listeners.append(self)
            oper.start()
            
        else:
            self.__started = False
            self._send_finished_event(SUCCESSFUL)
    
    
    
    def on_finished(self, evt):
        # Remove the listener connection
        evt.source.listeners.remove(self)
        
        # One more done
        self.__done += 1
        self.__curr_oper = None
        
        if self._stop_now and evt.id != ERROR:
            evt.id = ABORTED
            evt.source = self
            
        # when 'abort_on_failure' do it otherwise stop when 'stop_now' is
        # called
        if (self.abort_on_failure and evt.id != SUCCESSFUL) or self._stop_now:
            # Clear remaining operations
            self.__operations = []
            self._propagate(evt, self)
                
        else:
            # Start next operation
            self.__start_next()
    
    can_stop = property (lambda self: self.running and self.__curr_oper.can_stop)
    
    def stop(self):
        assert self.can_stop, "Check if the operation can be stopped first."
        self.__curr_oper.stop ()
    
    def pause(self):
        self.paused = True
    
    def stop_after_next(self):
        self._stop_now = True
    
    def __len__(self):
        return len(self.__operations)
    
    def __repr__ (self):
        return "{%s: %s}" % (
            super(OperationsQueue, self).__repr__(),
            self.__operations.__repr__()
        )

class SyncListener (OperationListener):
    def __init__ (self, mainloop):
        self.mainloop = mainloop
        
    def on_finished (self, event):
        self.result = event
        self.mainloop.quit ()
        
def syncOperation (oper):
    """
    This function can run an operation synchronously and returns the event
    object. This only affects GObject related operations.
    """
    
    mainloop = gobject.MainLoop ()
    
    listener = SyncListener (mainloop)
    oper.listeners.append (listener)
    oper.start ()
    mainloop.run ()
    return listener.result

def syncableMethod(kwarg="sync", default_value=False):
    """
    This is a decorator that accepts a keyword argument (defaults to 'sync')
    with a kwarg default value (defaults to `False`).
    When you call the method you can use the extra keyword argument to
    specify if the method call is going to be sync or async.
    
    The decorated method should be one that returns an operation.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                is_sync = kwargs[kwarg]
                del kwargs[kwarg]
            except KeyError:
                is_sync = default_value

            if is_sync:
                
                return syncOperation(func(*args, **kwargs))
            else:
                return func(*args, **kwargs)
        return wrapper
        
    return decorator

sync = syncableMethod(default_value=True)
async = syncableMethod()

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
    
