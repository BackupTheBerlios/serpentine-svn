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

import gtk
import gobject
import datetime

from gettext import gettext as _
from gettext import ngettext as N_

class NotFoundError(KeyError):
    """This is raised when an element is not found"""


class DictModelIterator:
    def __init__ (self, parent):
        self.parent = parent
        self.index = 0
        
    def __iter__ (self):
        return self
    
    def next (self):
        if len(self.parent) <= self.index:
            raise StopIteration
        
        ret = self.parent.get(self.index)
        self.index += 1
        return ret
        
class DictStore (gtk.ListStore):
    def __init__ (self, *cols):
        self.indexes = {}
        self.cols = []
        spec = []
        index = 0
        for col in cols:
            # Generate indexes dict
            self.indexes[col["name"]] = index
            spec.append (col["type"])
            self.cols.append (col["name"])
            index += 1
        gtk.ListStore.__init__ (self, *tuple(spec))
        
    def __dict_to_list (self, row):
        values = []
        for key in self.cols:
            values.append (row[key])
        return values
        
    def append (self, row):
        gtk.ListStore.append (self, self.__dict_to_list (row))
    
    def insert_before (self, iter, row):
        gtk.ListStore.insert_before (self, iter, self.__dict_to_list (row))
    
    def insert_after (self, iter, row):
        gtk.ListStore.insert_after (self, iter, self.__dict_to_list (row))
        
    def index_of (self, key):
        return self.indexes[key]
    def get (self, index):
        return DictModelRow(self, self[index])
    def __iter__ (self):
        return DictModelIterator(self)
        
gobject.type_register (DictStore)

class DictModelRow (object):
    def __init__ (self, parent, row):
        self.parent = parent
        self.row = row
        
    def __getitem__ (self, key):
        return self.row[self.parent.indexes[key]]
        
    def __setitem__ (self, key, value):
        self.row[self.parent.indexes[key]] = value
        
    def __delitem__ (self, key):
        del self.row[self.parent.indexes[key]]
    
    def keys(self):
        return self.parent.cols
    
    def get (self, key, default):
        if self.has_key (key):
            return self[key]
        return default
    
    def has_key (self, key):
        return key in self.keys()

    __contains__ = has_key

class SimpleListWrapper:
    def __init__ (self, store):
        self.store = store
        
    def __getitem__ (self, index):
        return self.store[index][0]
        
    def append (self, item):
        self.store.append ([item])

class SimpleList (gtk.TreeView):
    def __init__ (self, column_title, editable = True):
        gtk.TreeView.__init__(self)
        store = gtk.ListStore(str)
        self.set_model (store)
        rend = gtk.CellRendererText()
        if editable:
            rend.set_property ('editable', True)
            rend.connect ('edited', self.__on_text_edited)
            
        if not column_title:
            self.set_headers_visible (False)
            column_title = ""
        col = gtk.TreeViewColumn(column_title, rend, text = 0)
        self.append_column (col)
        self.wrapper = SimpleListWrapper (store)
        
    def get_simple_store(self):
        return self.wrapper
    
    def __on_text_edited (self, cell, path, new_text, user_data = None):
        self.get_model()[path][0] = new_text

gobject.type_register (SimpleList)

################################################################################
# rat.hig
dialog_error = \
    lambda primary_text, secondary_text, **kwargs:\
        hig_alert(
            primary_text,
            secondary_text,
            stock = gtk.STOCK_DIALOG_ERROR,
            buttons =(gtk.STOCK_CLOSE, gtk.RESPONSE_OK),
            **kwargs
        )
    

dialog_warn = \
    lambda primary_text, secondary_text, **kwargs:\
        hig_alert(
            primary_text,
            secondary_text,
            stock = gtk.STOCK_DIALOG_WARNING,
            buttons =(gtk.STOCK_CLOSE, gtk.RESPONSE_OK),
            **kwargs
        )

dialog_ok_cancel = \
    lambda primary_text, secondary_text, ok_button=gtk.STOCK_OK, \
        **kwargs: hig_alert(
            primary_text,
            secondary_text,
            stock = gtk.STOCK_DIALOG_WARNING,
            buttons =(
                gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                ok_button, gtk.RESPONSE_OK
            ),
            **kwargs)

dialog_info = \
    lambda primary_text, secondary_text, **kwargs:\
        hig_alert(
            primary_text,
            secondary_text,
            stock = gtk.STOCK_DIALOG_INFO,
            buttons =(gtk.STOCK_CLOSE, gtk.RESPONSE_OK),
            **kwargs
        )

class WidgetCostumizer:
    """
    The WidgetCostumizer is a class template for defining chaining of asseblies
    of interfaces. For example you can create a dialog with this simple lines of
    code::
    
        creator.bind(SetupDialog()).bind(SetupAlert(primary_text, secondary_text, **kwargs))
        dlg = creator()
    
    The costumization of a widget is like a pipeline of filters that act on a
    certain widget and on a toplevel container.
    
    """
    _to_attrs = True
    _defaults = {}
    _next_values = None
    _next_iter = None
    
    def __init__(self, *args, **kwargs):
        self._args  = args
        self._kwargs = dict(self._defaults)
        self._kwargs.update(kwargs)
        self._next_values = []
    
    def _get_next(self):
        return self._next_iter.next()
    
    def update(self, **kwargs):
        self._kwargs.update(kwargs)
    
    def _run(self, *args, **kwargs):
        pass
    
    def bind(self, *others):
        for other in others:
            if not isinstance(other, WidgetCostumizer):
                raise TypeError(type(other))
            
            self._next_values.append(other)

        return self
    
    def _call(self, widget, container):
        if self._to_attrs:
            for key, value in self._kwargs.iteritems():
                setattr(self, key, value)
            
        widget, container = self._run(widget, container)
        
        for costum in self._next_values:
            widget, container = costum._call(widget, container)
        
        for key in self._kwargs:
            delattr(self, key)
        return widget, container
        
    def __call__(self, widget = None, container = None):
        """This method is only called once"""
        return self._call(widget, container)[0]

class SetupScrolledWindow(WidgetCostumizer):
    def _run(self, scrolled, container):
        assert container is None

        if scrolled is None:
            scrolled = gtk.ScrolledWindow()
        
        scrolled.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        return scrolled, None
        
class SetupLabel(WidgetCostumizer):
    """
    Usage::

        lbl = SetupLabel("<b>foo</b>")(gtk.Label())
        lbl.show()
        
    Or::
    
        lbl = SetupLabel("<b>foo</b>")()
        lbl.show()
    
    """
    def _run(self, lbl, container):
        assert container is None
        assert len(self._args) == 0 or len(self._args) == 1
        
        if lbl is None:
            lbl = gtk.Label()
            
        lbl.set_alignment(0, 0)
        
        if len(self._args) == 1:
            lbl.set_markup(self._args[0])
            
        lbl.set_selectable(True)
        lbl.set_line_wrap(True)
        
        return lbl, container
            
def dialog_decorator(func):
    def wrapper(self, dialog, container):
        if container is None:
            container = dialog.get_child()
        return func(self, dialog, container)
        
    return wrapper

class SetupDialog(WidgetCostumizer):
    def _run(self, dialog, container):
        dialog.set_border_width(4)
        dialog.set_has_separator(False)
        dialog.set_title("")
        dialog.set_resizable(False)

        align = gtk.Alignment()
        align.set_padding(
            padding_top = 0,
            padding_bottom = 7,
            padding_left = 0,
            padding_right = 0
        )
        align.set_border_width(5)
        align.show()
        container.add(align)
        
        return dialog, align
    
    _run = dialog_decorator(_run)


class SetupAlert(WidgetCostumizer):
    class _PrimaryTextDecorator:
        def __init__(self, label):
            self.label = label
            
        def __call__(self, primary_text):
            self.label.set_markup(
                '<span weight="bold" size="larger">'+primary_text+'</span>'
            )
        
            
    _defaults = {
        "title": "",
        "stock": gtk.STOCK_DIALOG_INFO
    }
    
    def _before_text(self, dialog, vbox):
        pass
    
    def _after_text(self, dialog, vbox):
        pass
    
    def _run(self, dialog, container):
        primary_text, secondary_text = self._args

        dialog.set_title(self.title)

        hbox = gtk.HBox(spacing = 12)
        hbox.set_border_width(0)
        hbox.show()
        container.add(hbox)
        
        img = gtk.Image()
        img.set_from_stock(self.stock, gtk.ICON_SIZE_DIALOG)
        img.set_alignment(img.get_alignment()[0], 0.0)
        img.show()
        hbox.pack_start(img, False, False)
        
        vbox = gtk.VBox(spacing = 6)
        vbox.show()
        hbox.pack_start(vbox)
        
        
        lbl = SetupLabel(
            '<span weight="bold" size="larger">'+primary_text+'</span>'
        )()
        lbl.show()
        
        
        dialog.set_primary_text = self._PrimaryTextDecorator(lbl)
        
        vbox.pack_start(lbl, False, False)
        
        lbl = SetupLabel(secondary_text)()
        lbl.show()
        dialog.set_secondary_text = lbl.set_text
        
        def on_destroy(widget):
            delattr(widget, "set_secondary_text")
            delattr(widget, "set_primary_text")
        
        dialog.connect("destroy", on_destroy)
        
        self._before_text(dialog, vbox)
        vbox.pack_start(lbl, False, False)
        self._after_text(dialog, vbox)
        
        return dialog, vbox

    _run = dialog_decorator(_run)


class SetupRadioChoiceList(SetupAlert):
    
    def _after_text(self, dialog, container):
        vbox = gtk.VBox(spacing=6)
        vbox.show()
        vbox.set_name("items")
        
        container.pack_start(vbox)
        group = None
        for item in self.items:
            radio = gtk.RadioButton(group, item)
            radio.show()
            
            if group is None:
                group = radio
            
            vbox.pack_start(radio, False, False)
            
class SetupListAlertTemplate(SetupAlert):
    def get_list_title(self):
        raise NotImplementedError
    
    def configure_widgets(self, dialog, tree):
        raise NotImplementedError

    def create_store(self):
        raise NotImplementedError
    
    def _before_text(self, dialog, vbox):
        store = self.create_store()
        
        title = self.get_list_title()
        
        if title is not None:
            lbl = SetupLabel(title)()
            lbl.show()
            vbox.pack_start(lbl, False, False)
        
        tree = gtk.TreeView()
        tree.set_name("list_view")
        tree.set_model(store)
        tree.set_headers_visible(False)

        tree.show()
        scroll = SetupScrolledWindow()()
        scroll.add(tree)
        scroll.show()
        
        vbox.add(scroll)

        self.configure_widgets(dialog, tree)

        return dialog, vbox

class SetupMultipleChoiceList(SetupListAlertTemplate):

    def get_list_title(self):
        return self.list_title

    def configure_widgets(self, dialog, tree):
        store = tree.get_model()
        
        
        # Create the callback
        def on_toggle(render, path, args):
            dialog, model, min_sel, max_sel = args
            
            tree_iter = model.get_iter(path)
            row = model[tree_iter]
            row[0] = not row[0]
            
            if row[0]:
                model.enabled_rows += 1
            else:
                model.enabled_rows -= 1
            
            if model.enabled_rows == 0:
                is_sensitive = False
            elif max_sel >= 0:
                is_sensitive = min_sel <= model.enabled_rows <= max_sel
            else:
                is_sensitive = min_sel <= model.enabled_rows
            
            dialog.set_response_sensitive(gtk.RESPONSE_OK, is_sensitive)
        
        args = (dialog, store, self.min_select, self.max_select)

        rend = gtk.CellRendererToggle()
        rend.connect("toggled", on_toggle, args)
        col = gtk.TreeViewColumn("", rend, active = 0)
        tree.append_column(col)

        rend = gtk.CellRendererText()
        col = gtk.TreeViewColumn("", rend, text = 1)
        tree.append_column(col)

        dialog.set_response_sensitive(gtk.RESPONSE_OK, False)


    def create_store(self):
        store = gtk.ListStore(gobject.TYPE_BOOLEAN, gobject.TYPE_STRING)
        store.enabled_rows = 0
        for item in self.items:
            store.append((False, item))
        return store


class SetupListAlert(SetupListAlertTemplate):
    
    _defaults = {
        "list_title": None
    }
    _defaults.update(SetupAlert._defaults)
    
    def get_list_title(self):
        return self.list_title

    def configure_widgets(self, dialog, tree):
        rend = gtk.CellRendererText()
        col = gtk.TreeViewColumn("", rend, text = 0)
        tree.append_column(col)
        tree.get_selection().set_mode(gtk.SELECTION_NONE)


    def create_store(self):
        store = gtk.ListStore(gobject.TYPE_STRING)

        for item in self.items:
            store.append((item,))

        return store
    

class SetupSingleChoiceList(SetupListAlert):

    _defaults = {
        "min_select": 1,
    }
    
    _defaults.update(SetupListAlert._defaults)

    def configure_widgets(self, dialog, tree):
        assert self.min_select in (0, 1)
        
        SetupListAlert.configure_widgets(self, dialog, tree)
        selection = tree.get_selection()

        if self.min_select == 0:
            selection_mode = gtk.SELECTION_SINGLE
            def on_selection_changed(selection, dialog):
                is_sensitive = selection.count_selected_rows() > 0
                dialog.set_response_sensitive(gtk.RESPONSE_OK, is_sensitive)
            selection.connect("changed", on_selection_changed, dialog)
            
        else:
            selection_mode = gtk.SELECTION_BROWSE

        selection.set_mode(selection_mode)
    


class RunDialog(WidgetCostumizer):
    """
    This is a terminal costumizer because it swaps the gtk.Dialog recieved by
    argument for its `gtk.Dialog.run`'s result.
    """
    def _run(self, dialog, container):
        response = dialog.run()
        dialog.destroy()
        return response, None
        
def hig_alert(primary_text, secondary_text, parent = None, flags = 0, \
              buttons =(gtk.STOCK_OK, gtk.RESPONSE_OK), run = True, \
              _setup_alert = SetupAlert, **kwargs):
              
    if parent is None and "title" not in kwargs:
        raise TypeError("When you don't define a parent you must define a "
                        "title") 
    dlg = gtk.Dialog(parent = parent, flags = flags, buttons = buttons)

    costumizer = SetupDialog()
    
    costumizer.bind(_setup_alert(primary_text, secondary_text, **kwargs))

    if run:
        costumizer.bind(RunDialog())

    return costumizer(dlg)


def list_dialog(primary_text, secondary_text, parent=None, items=(), **kwargs):
    """
    @param list_title: A label will be placed above the list of items describing
        what's the content of the list. Optional.
    
    Every other argument that L{hig_alert} function does.
    
    Example::
        primary_text = "Listing cool stuff"
        secondary_text = "To select more of that stuff eat alot of cheese!"
        list_title = "Your cool stuff:"
        # Some random 20 elements
        items = ["foo", "bar"] * 10
        window_title = "Rat Demo"
        list_dialog(
            primary_text,
            secondary_text,
            items=items,
            title=window_title,
            list_title=list_title
        )
    """
    return hig_alert(
        primary_text,
        secondary_text,
        parent = parent,
        _setup_alert = SetupListAlert,
        items = items,
        **kwargs
    )

################
# choice_dialog
class _OneStrategy:
    accepts = lambda self, choices, min_select, max_select: choices == 1
    
    def before(self, kwargs):
        pass

    def get_items(self, data):
        return (0,)

class _BaseStrategy:

    def before(self, kwargs):
        kwargs["_setup_alert"] = self.setup_factory


class _MultipleStrategy(_BaseStrategy):
    accepts = lambda self, choices, min_select, max_select: max_select == -1 or\
                                                            max_select > 1
    setup_factory = SetupMultipleChoiceList

    def get_items(self, dlg):
        # Multiple selection
        store = find_child_widget(dlg, "list_view").get_model()
        return tuple(row.path[0] for row in store if row[0])

class _RadioStrategy(_BaseStrategy):

    accepts = lambda self, choices, min_select, max_select: choices < 5
    setup_factory = SetupRadioChoiceList
    
    def get_items(self, dlg):
        vbox = find_child_widget(dlg, "items")
        counter = 0
        for radio in vbox.get_children():
            if radio.get_active():
                break
            counter += 1
        assert radio.get_active()
            
        return (counter,)

class _SingleListStrategy(_BaseStrategy):
    accepts = lambda self, a, b, c: True
    setup_factory = SetupSingleChoiceList
    def get_items(self, dlg):
        list_view = find_child_widget(dlg, "list_view")
        rows = list_view.get_selection().get_selected_rows()[1]
        get_element = lambda row: row[0]

        items = tuple(map(get_element, rows))
        
_STRATEGIES = (_OneStrategy, _MultipleStrategy, _RadioStrategy,
               _SingleListStrategy)
_STRATEGIES = tuple(factory() for factory in _STRATEGIES)

def choice_dialog(primary_text, secondary_text, parent=None, \
                                                allow_cancel=True, **kwargs):
    """
    @param items: the items you want to choose from
    @param list_title: the title of the list. Optional.
    @param allow_cancel: If the user can cancel/close the dialog.
    @param min_select: The minimum number of elements to be selected.
    @param max_select: The maximum number of elements to be selected.
        -1 Means no limit.
    
    @param dialog_callback: This is a callback function that is going to be
        called when the dialog is created. The argument is the dialog object.
    @param one_item_text: when specified and if the number of `items` is one
        this text will be the primary text. This string must contain a '%s'
        which will be replaced by the item value.
        Optional.
    """

    if "run" in kwargs:
        del kwargs["run"]
    
    choices = len(kwargs["items"])
    min_select = kwargs.get("min_select", 1)
    max_select = kwargs.get("max_select", -1)

    # Make sure the arguments are correct
    assert choices > 0
    assert (max_select == -1) ^ (min_select <= max_select <= choices)
    assert 0 <= min_select <= choices
    
    buttons = (kwargs.get("ok_button", gtk.STOCK_OK), gtk.RESPONSE_OK)
    
    if allow_cancel:
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL) + buttons
    else:
        # TODO: make closing the window impossible    
        pass

    if min_select == 0:
        txt = N_("Don't select it", "Don't select any items", choices)
        txt = kwargs.get("skip_button", txt)
        buttons = (txt, gtk.RESPONSE_CLOSE) + buttons
    
    for strategy in _STRATEGIES:
        if strategy.accepts(choices, min_select, max_select):
            break
    assert strategy.accepts(choices, min_select, max_select)
    
    if choices == 1:
        if "one_item_text" in kwargs:
            primary_text = kwargs["one_item_text"] % kwargs["items"][0]
    
    data = strategy.before(kwargs)
    if data is not None:
        primary_text = data
    
    dlg = hig_alert(
        primary_text,
        secondary_text,
        parent = parent,
        run = False,
        buttons = buttons,
        **kwargs
    )
    kwargs.get("dialog_callback", lambda foo: None)(dlg)
    response = dlg.run()
    
    if response != gtk.RESPONSE_OK:
        dlg.destroy()
        return (), response
    
    items = strategy.get_items(dlg)
    dlg.destroy()
    
    return items, response
    
#########
# save_changes
MIN_FRACTION = 60
HOUR_FRACTION = 60 * MIN_FRACTION
DAY_FRACTION = 24 * HOUR_FRACTION
def humanize_seconds(elapsed_seconds, use_hours = True, use_days = True):
    """
    Turns a number of seconds into to a human readable string, example
    125 seconds is: '2 minutes and 5 seconds'.
    
    @param elapsed_seconds: number of seconds you want to humanize
    @param use_hours: wether or not to render the hours(if hours > 0)
    @param use_days: wether or not to render the days(if days > 0)
    """
    
    text = []
    
    duration = elapsed_seconds
    
    if duration == 0:
        return _("0 seconds")
    
    days = duration / DAY_FRACTION
    if use_days and days > 0:
        text.append(N_("%d day", "%d days", days) % days)
        duration %= DAY_FRACTION
        
    hours = duration / HOUR_FRACTION
    if use_hours and hours > 0:
        text.append(N_("%d hour", "%d hours", hours) % hours)
        duration %= HOUR_FRACTION
    
    minutes = duration / MIN_FRACTION
    if minutes > 0:
        text.append(N_("%d minute", "%d minutes", minutes) % minutes)
        duration %= MIN_FRACTION

    seconds = duration % 60
    if seconds > 0:
        text.append(N_("%d second", "%d seconds", seconds) % seconds)
    
    if len(text) > 2:
        # To translators: this joins 3 or more time fractions
        return _(", ").join(text[:-1]) + _(" and ") + text[-1]
    else:
        # To translators: this joins 2 or 1 time fractions
        return _(" and ").join(text)

class _TimeUpdater:
    def __init__(self, initial_time):
        self.initial_time = initial_time
    
    def set_dialog(self, dialog):
        self.dialog = dialog
        self.dialog.connect("response", self.on_response)
        self.source = gobject.timeout_add(500, self.on_tick)
    
    def on_response(self, *args):
        gobject.source_remove(self.source)

    def get_text(self):
        last_changes = datetime.datetime.now() - self.initial_time
        # To translators %s is the time
        secondary_text = _("If you don't save, changes from the last %s "
                           "will be permanently lost.")
        return secondary_text % humanize_seconds(last_changes.seconds)
        
        
    def on_tick(self):
        self.dialog.set_secondary_text(self.get_text())
        return True

def save_changes(files, last_save=None, parent=None, **kwargs):
    """
    Shows up a Save changes dialog to a certain list of documents and returns
    a tuple with two values, the first is a list of files that are to be saved
    the second is the value of the response, which can be one of:
      - gtk.RESPONSE_OK - the user wants to save
      - gtk.RESPONSE_CANCEL - the user canceled the dialog
      - gtk.RESPONSE_CLOSE - the user wants to close without saving
      - gtk.RESPONSE_DELETE_EVENT - the user closed the window
    
    So if you want to check if the user canceled just check if the response is
    equal to gtk.RESPONSE_CANCEL or gtk.RESPONSE_DELETE_EVENT
    
    When the `elapsed_time` argument is not `None` it should be a list of the
    elapsed time since each was modified. It must be in the same order of
    the `files` argument.
    
    This function also accepts every argument that a hig_alert function accepts,
    which means it accepts `title`, etc. Note that this function overrides
    the `run` argument and sets it to True, because it's not possible for a user
    to know which files were saved since the dialog changes is structure
    depending on the arguments.
    
    Simple usage example::
        files_to_save, response = save_changes(["foo.bar"])

    @param files: a list of filenames to be saved
    @param last_save: when you only want to save one file you can optionally
        send the date of when the user saved the file most recently.
        
    @type last_save: datetime.datetime
    @param parent: the window that will be parent of this window.
    @param primary_text: optional, see hig_alert.
    @param secondary_text: optional, see hig_alert.
    @param one_item_text: optional, see choice_alert.
    @param list_title: optional, see choice_alert.
    @param kwargs: the remaining keyword arguments are the same as used on the function
        hig_alert.
    @return: a tuple with a list of entries the user chose to save and a gtk.RESPONSE_*
        from the dialog
    """
    primary_text = N_("There is %d file with unsaved changes. "
                      "Save changes before closing?",
                      "There are %d files with unsaved " 
                      "changes. Save changes before closing?", len(files)) 

    primary_text %= len(files)
    
    primary_text = kwargs.get("primary_text", primary_text)
    
    secondary_text = _("If you don't save, all your changes will be "
                       "permanently lost.")
    
    secondary_text = kwargs.get("secondary_text", secondary_text)

    one_item_text = _("Save the changes to <i>%s</i> before closing?")
    one_item_text = kwargs.get("one_item_text", one_item_text)
    
    list_title = _("Select the files you want to save:")
    list_title = kwargs.get("list_title", list_title)
    
    if len(files) == 1 and last_save is not None:
        updater = _TimeUpdater(last_save)
        secondary_text = updater.get_text()
        kwargs["dialog_callback"] = updater.set_dialog
        
    indexes, response = choice_dialog(
        primary_text,
        secondary_text,
        min_select = 0,
        max_select = -1,
        skip_button = _("Close without saving"),
        ok_button = gtk.STOCK_SAVE,
        list_title = list_title,
        items = files,
        one_item_text = one_item_text,
        **kwargs
    )

    return map(files.__getitem__, indexes), response

################################################################################

# widget iterators
def _simple_iterate_widget_children(widget):
    """This function iterates all over the widget children.
    """
    get_children = getattr(widget, "get_children", None)

    if get_children is None:
        return
    
    for child in get_children():
        yield child

    get_submenu = getattr(widget, "get_submenu", None)
    
    if get_submenu is None:
        return
    
    sub_menu = get_submenu()
    
    if sub_menu is not None:
        yield sub_menu

class _IterateWidgetChildren:
    """This iterator class is used to recurse to child widgets, it uses
    the _simple_iterate_widget_children function
    
    """
    def __init__(self, widget):
        self.widget = widget
        self.children_widgets = iter(_simple_iterate_widget_children(self.widget))
        self.next_iter = None
        
    def next(self):
        if self.next_iter is None:
            widget = self.children_widgets.next()
            self.next_iter = _IterateWidgetChildren(widget)
            return widget
            
        else:
            try:
                return self.next_iter.next()
            except StopIteration:
                self.next_iter = None
                return self.next()

    def __iter__(self):
        return self
        
def iterate_widget_children(widget, recurse_children = False):
    """
    This function is used to iterate over the children of a given widget.
    You can recurse to all the widgets contained in a certain widget.
    
    @param widget: The base widget of iteration
    @param recurse_children: Wether or not to iterate recursively, by iterating
        over the children's children.
    
    @return: an iterator
    @rtype: C{GeneratorType}
    """
    if recurse_children:
        return _IterateWidgetChildren(widget)
    else:
        return iter(_simple_iterate_widget_children(widget))

def iterate_widget_parents(widget):
    """Iterate over the widget's parents.

    @param widget: The base widget of iteration
    @return: an iterator
    @rtype: C{GeneratorType}
    """
    
    widget = widget.get_parent()
    while widget is not None:
        yield widget
        widget = widget.get_parent()

def find_parent_widget(widget, name, find_self=True):
    """
    Finds a widget by name upwards the tree, by searching self and its parents
    
    @return: C{None} when it didn't find it, otherwise a C{gtk.Container}
    @rtype: C{gtk.Container}
    @param find_self: Set this to C{False} if you want to only find on the parents
    @param name: The name of the widget
    @param widget: The widget where this function will start searching
    """
    
    assert widget is not None

    if find_self and widget.get_name() == name:
        return widget

    for w in iterate_widget_parents(widget):
        if w.get_name() == name:
            return w

    raise NotFoundError(name)

def find_child_widget(widget, name, find_self=True):
    """
    Finds the widget by name downwards the tree, by searching self and its
    children.

    @return: C{None} when it didn't find it, otherwise a C{gtk.Widget}
    @rtype: C{gtk.Widget}
    @param find_self: Set this to L{False} if you want to only find on the children
    @param name: The name of the widget
    @param widget: The widget where this function will start searching
    """
    
    assert widget is not None
    
    if find_self and widget.get_name() == name:
        return widget
    
    for w in iterate_widget_children(widget, True):

        if name == w.get_name():
            return w
    
    raise NotFoundError(name)

        

def get_root_parent(widget):
    """Returns the first widget of a tree. If this widget has no children
    it will return C{None}
    
    @return: C{None} when there is no parent widget, otherwise a C{gtk.Container}
    @rtype: C{gtk.Container} 
    """
    parents = list(iterate_widget_parents(widget))
    if len(parents) == 0:
        return None
    else:
        return parents[-1]

