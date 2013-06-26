#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# forked from https://github.com/robbeofficial/spotifyripper
# features
#     - real-time VBR ripping from spotify PCM stream
#     - writes id3 tags v1.1 compatible with old mp3 players
#     - creates files and directories based on the following structure Artist/Album/01 - Artist - Song.mp3
# 
# prerequisites:
#     - libspotify (download at https://developer.spotify.com/technologies/libspotify/)
#     - pyspotify (sudo pip install -U pyspotify)
#     - spotify appkey (download at developer.spotify.com, requires premium!)
#     - lame
#     - eyeD3 (pip install eyeD3)

from subprocess import call, Popen, PIPE
from spotify import Link, Image
from jukebox import Jukebox, container_loaded
import os, sys
import threading
import time

playback = False # set if you want to listen to the tracks that are currently ripped (start with "padsp ./jbripper.py ..." if using pulse audio)

pipe = None
ripping = False
end_of_track = threading.Event()

def printstr(str): # print without newline
    sys.stdout.write(str)
    sys.stdout.flush()

def shell(cmdline): # execute shell commands (unicode support)
    call(cmdline, shell=True)

def rip_init(session, track):
    global pipe, ripping
    num_track = "%02d" % (track.index(),)
    mp3file = str(num_track) + " - " + track.artists()[0].name() + " - " + track.name() + ".mp3"
    directory = os.getcwd() + "/" + track.artists()[0].name() + "/" + track.album().name() + "/"
    print directory
    if not os.path.exists(directory):
        os.makedirs(directory)
    printstr("ripping " + mp3file + " ...")
    p = Popen("lame --silent -V2 -h -r - \""+ directory + mp3file+"\"", stdin=PIPE, shell=True)
    pipe = p.stdin
    ripping = True

def rip_terminate(session, track):
    global ripping
    if pipe is not None:
        print(' done!')
        pipe.close()
    ripping = False    

def rip(session, frames, frame_size, num_frames, sample_type, sample_rate, channels):
    if ripping:
        printstr('.')
        pipe.write(frames);

def rip_id3(session, track): # write ID3 data
    num_track = "%02d" % (track.index(),)
    mp3file = str(num_track) + " - " + track.artists()[0].name() + " - " + track.name()+".mp3"
    artist = track.artists()[0].name()
    album = track.album().name()
    title = track.name()
    year = track.album().year()
    directory = os.getcwd() + "/" + track.artists()[0].name() + "/" + track.album().name() + "/"
    cmd = "eyeD3" + \
	  " -1 " + \
          " -t \"" + title + "\"" + \
          " -a \"" + artist + "\"" + \
          " -A \"" + album + "\"" + \
          " -n " + str(num_track) + \
          " -Y " + str(year) + \
          " \"" + directory + mp3file + "\""
    shell(cmd)

class RipperThread(threading.Thread):
    def __init__(self, ripper):
        threading.Thread.__init__(self)
        self.ripper = ripper

    def run(self):
        # wait for container
        container_loaded.wait()
        container_loaded.clear()

        # create track iterator
        link = Link.from_string(sys.argv[3])
        if link.type() == Link.LINK_TRACK:
            track = link.as_track()
            itrack = iter([track])
        elif link.type() == Link.LINK_PLAYLIST:
            playlist = link.as_playlist()
            print('loading playlist ...')
            while not playlist.is_loaded():
                time.sleep(0.1)
            print('done')
            itrack = iter(playlist)

        # ripping loop
        session = self.ripper.session
        for track in itrack:
            
                self.ripper.load_track(track)

                rip_init(session, track)

                self.ripper.play()

                end_of_track.wait()
                end_of_track.clear() # TODO check if necessary

                rip_terminate(session, track)
                rip_id3(session, track)

        self.ripper.disconnect()

class Ripper(Jukebox):
    def __init__(self, *a, **kw):
        Jukebox.__init__(self, *a, **kw)
        self.ui = RipperThread(self) # replace JukeboxUI
        self.session.set_preferred_bitrate(2) # 320 bps

    def music_delivery_safe(self, session, frames, frame_size, num_frames, sample_type, sample_rate, channels):
        rip(session, frames, frame_size, num_frames, sample_type, sample_rate, channels)
        if playback:
            return Jukebox.music_delivery_safe(self, session, frames, frame_size, num_frames, sample_type, sample_rate, channels)
        else:
            return num_frames

    def end_of_track(self, session):
        Jukebox.end_of_track(self, session)
        end_of_track.set()


if __name__ == '__main__':
	if len(sys.argv) >= 3:
		ripper = Ripper(sys.argv[1],sys.argv[2]) # login
		ripper.connect()
	else:
		print "spotify-to-mp3\n"
		print "usage : \n"
		print "	  ./jbripper.py [username] [password] [spotify_url]"
		print "example : \n"
	 	print "   ./jbripper.py user pass spotify:track:52xaypL0Kjzk0ngwv3oBPR - for a single file"
		print "   ./jbripper.py user pass spotify:user:username:playlist:4vkGNcsS8lRXj4q945NIA4 - rips entire playlist"