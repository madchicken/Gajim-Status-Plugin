#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright 2006 Pierpaolo FOllia <pfollia@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import rhythmdb, rb
import gobject, gtk
import dbus
import gtk
import gtk.glade
import gconf
import sys

from string import join

GCONF_PATH = '/apps/rhythmbox/plugins/gajim-status/'
GCONF_VALUE_STATUS_TEXT = 'status_text'
GCONF_VALUE_STATUS_TEXT_NO_MUSIC = 'status_text_no_music'
VERSION = '0.4'
DEFAULT_STATUS_MESSAGE = '♫ #title by #artist'
DEFAULT_STATUS_MESSAGE_NO_MUSIC = 'Sorry, no music now'


class GajimStatus(rb.Plugin):

	def __init__(self):
		rb.Plugin.__init__(self)
			
	def activate(self, shell):
		print 'activating gajim status message plugin'
		self.sp = shell.get_player ()
		self.db = shell.get_property('db')
		self.gajim_prefs = GajimStatusPreferences(self)
		self.is_playing = self.sp.get_playing()
		self.last_status_message = ''
		#Connect to "play song" event playing-changed
		self.pc_id = self.sp.connect('playing-changed', self.playing_changed)
		self.psc_id = self.sp.connect('playing-song-changed', self.playing_entry_changed)
		try:
			self.gajim_interface = dbus.Interface(dbus.SessionBus().get_object('org.gajim.dbus', '/org/gajim/dbus/RemoteObject'), 'org.gajim.dbus.RemoteInterface')
		except:
			print 'Gajim not running. Plugin disabled'
		#Change the message if there is something playing now...
		self.accounts = self.gajim_interface.list_accounts()
		self.gajim_old_message = {}
		for account in self.accounts:
			self.gajim_old_message[account] = self.gajim_interface.get_status_message(account)
		self.playing_entry_changed (self.sp, self.sp.get_playing_entry ())
	
	def deactivate(self, shell):
		print 'deactivating sample python plugin'
		#status = self.gajim_prefs.status_text_no_music
		if self.gajim_interface is not None:
			for account in self.accounts:
				self.gajim_interface.change_status(self.gajim_interface.get_status(""), self.gajim_old_message[account], account)
		self.sp.disconnect (self.psc_id)
		self.sp.disconnect (self.pc_id)

	def playing_changed(self, sp, entry):
		if self.gajim_interface is not None:
			if self.sp.get_playing() == False:
				status = self.last_status_message + ' [paused]'
				t = self.gajim_interface.get_status("")
				self.gajim_interface.change_status(t, status,"")
			else:
				status = self.last_status_message
				t = self.gajim_interface.get_status("")
				self.gajim_interface.change_status(t, status,"")
				
		self.is_playing = self.sp.get_playing()
	
	def playing_entry_changed(self, sp, entry):
		if self.gajim_interface is not None:
			print 'song changed, changing status for gajim...'
			self.last_entry = entry

			self.change_status_message()

	def create_configure_dialog(self):
		return self.gajim_prefs.create_window()

	def change_status_message(self):
		print str(self.last_entry)
		if(self.last_entry is not None):
			t = self.gajim_interface.get_status("")
			print t
			if t == 'online':
				artist = self.db.entry_get(self.last_entry, rhythmdb.PROP_ARTIST)
				title = self.db.entry_get(self.last_entry, rhythmdb.PROP_TITLE)
				album = self.db.entry_get(self.last_entry, rhythmdb.PROP_ALBUM)
				genre = self.db.entry_get(self.last_entry, rhythmdb.PROP_GENRE)
				track = self.db.entry_get(self.last_entry, rhythmdb.PROP_TRACK_NUMBER)

				status = self.gajim_prefs.status_text
				if artist is not None:
					status = status.replace('#artist', artist)
				if title is not None:
					status = status.replace('#title', title)
				if album is not None:
					status = status.replace('#album', album)
				if genre is not None:
					status = status.replace('#genre', genre)
				if track is not None:
					status = status.replace('#track', str(track))

				if self.sp.get_playing() == False:
					status = status + ' [paused]'

				self.gajim_interface.change_status(t, status, "")
				self.last_status_message = status
		else:
			t = self.gajim_interface.get_status("")
			self.gajim_interface.change_status(t, self.gajim_prefs.status_text_no_music, "")

class GajimStatusPreferences:
	def __init__(self, plugin):
		self.plugin = plugin
		self.conf_client = gconf.client_get_default()
		self.conf_client.add_dir(GCONF_PATH, gconf.CLIENT_PRELOAD_NONE)
		# Connect the status_message and status_message_no_music to a callback that can change it when the option
		# is changed by some outside program.
		self.conf_client.notify_add(GCONF_PATH + GCONF_VALUE_STATUS_TEXT, self.gconf_status_message_changed);
		self.conf_client.notify_add(GCONF_PATH + GCONF_VALUE_STATUS_TEXT_NO_MUSIC, self.gconf_status_message_no_music_changed);

		self.status_text = self.conf_client.get_string(GCONF_PATH + GCONF_VALUE_STATUS_TEXT)
		self.status_text_no_music = self.conf_client.get_string(GCONF_PATH + GCONF_VALUE_STATUS_TEXT_NO_MUSIC)
		if(self.status_text is None):
			self.status_text = DEFAULT_STATUS_MESSAGE
		if(self.status_text_no_music is None):
			self.status_text_no_music = DEFAULT_STATUS_MESSAGE_NO_MUSIC

	def create_window(self):
		co = sys._getframe(1).f_code
		filename = co.co_filename
		filename = filename.replace('.py', '.glade')
		print 'Loading glade file: ' + filename
		self.widgets = gtk.glade.XML (filename, 'gajim-status')
		self.win = self.widgets.get_widget('gajim-status')
		self.widgets.get_widget('status_text').set_text(self.status_text)
		self.widgets.get_widget('status_text_no_music').set_text(self.status_text_no_music)
		#connect the UI to python code...
		self.widgets.get_widget('okbutton').connect('clicked', self.on_clicked_okbutton, '')
		self.widgets.get_widget('cancelbutton').connect('clicked', self.on_clicked_cancelbutton, '')
		self.widgets.get_widget('status_text').connect('changed', self.on_changed_status_message)
		self.widgets.get_widget('status_text_no_music').connect('changed', self.on_changed_status_message_no_music)
		return self.win

	def gconf_status_message_changed(self, client, connection_id, entry, args):
		# Make sure the preference has a valid value
		if (entry.get_value().type == gconf.VALUE_STRING):
			# Get the new value
			new_setting = entry.get_value().get_string()
			# Try to handle asynchronous-ness of GConf and prevent calling
			# checkbutton_toggled again if this function was called as a
			# result of the self.conf_client.set() function call.
			if (new_setting != self.status_text):
				self.status_text = new_setting
				self.plugin.change_status_message()
				if(self.win is not None):
					self.widgets.get_widget('status_text').set_text(self.status_text)

	def gconf_status_message_no_music_changed(self, client, connection_id, entry, args):
		# Make sure the preference has a valid value
		if (entry.get_value().type == gconf.VALUE_STRING):
			# Get the new value
			new_setting = entry.get_value().get_string()
			# Try to handle asynchronous-ness of GConf and prevent calling
			# checkbutton_toggled again if this function was called as a
			# result of the self.conf_client.set() function call.
			if (new_setting != self.status_text_no_music):
				self.status_text_no_music = new_setting
				self.plugin.change_status_message()
				if(self.win is not None):
					self.widgets.get_widget('status_text_no_music').set_text(self.status_text_no_music)

	def on_clicked_okbutton(self, button, data = None):
		self.conf_client.set_string(GCONF_PATH + GCONF_VALUE_STATUS_TEXT, self.status_text)
		self.conf_client.set_string(GCONF_PATH + GCONF_VALUE_STATUS_TEXT_NO_MUSIC, self.status_text_no_music)
		self.plugin.change_status_message()
		self.win.destroy()
		self.win = None

	def on_clicked_cancelbutton(self, button, data = None):
		self.win.destroy()
		self.win = None

	def on_changed_status_message(self, message):
		self.status_text = message.get_text()

	def on_changed_status_message_no_music(self, message):
		self.status_text_no_music = message.get_text()
