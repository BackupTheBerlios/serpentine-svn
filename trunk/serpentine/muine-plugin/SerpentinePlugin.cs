/*
 * Copyright (C) 2005 Tiago Cogumbreiro <cogumbreiro@users.sf.net>
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public
 * License along with this program; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */


using System;
using System.Diagnostics;
using Muine.PluginLib;


namespace Muine.Serpentine
{
    public class SerpentinePlugin: Plugin
    {
		
        public override void Initialize (IPlayer player)
        {
        	Gtk.ActionEntry[] actionEntries = new Gtk.ActionEntry[] {
        		new Gtk.ActionEntry (
        			"SerpentineBurn",
        			null,
        			"Record Playlist to disc...",
        			"",
        			null,
        			new EventHandler (this.runSerpentine)
        		),
        	};
			Gtk.ActionGroup actionGroup = new Gtk.ActionGroup("ShuffleActions");
			actionGroup.Add(actionEntries);

			player.UIManager.InsertActionGroup(actionGroup, -1);
			player.UIManager.AddUi(player.UIManager.NewMergeId(), "/MenuBar/FileMenu/ExtraFileActions", "SerpentineMenuItem", "SerpentineBurn", Gtk.UIManagerItemType.Menuitem, false);
        	
        }
        
        private void runSerpentine (object obj, System.EventArgs args) 
        {
        	//Console.WriteLine ("Running serpentine");
        	
        	ProcessStartInfo ps = new ProcessStartInfo ("serpentine", "-w ~/.gnome2/muine/playlist.m3u");
        	ps.UseShellExecute = true;
        	
        	Process p = new Process ();
        	// Listening when process exits
        	// http://msdn.microsoft.com/library/default.asp?url=/library/en-us/cpref/html/frlrfsystemdiagnosticsprocessclasssynchronizingobjecttopic.asp
        	p.Exited += new EventHandler (onFinish);
        	p.StartInfo = ps;
        	p.EnableRaisingEvents = true;
        	p.Start ();
        }
        
        private void onFinish (object obj, System.EventArgs args) 
        {
        	//Console.WriteLine ("Serpentine closed");
        }
    }
}
