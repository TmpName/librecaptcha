# Copyright (C) 2017, 2019 nickolas360 <contact@nickolas360.com>
#
# This file is part of librecaptcha.
#
# librecaptcha is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# librecaptcha is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with librecaptcha.  If not, see <http://www.gnu.org/licenses/>.
import base64
import os
import re
import xbmcaddon
import xbmcvfs

from resources.lib.comaddon import progress, dialog, xbmc, xbmcgui, VSlog

from .errors import UserError
from .frontend import Frontend

from threading import Thread, RLock
from queue import Queue
import json
import os
import sys
import time

Objectif = ""

class CliSolver:
    def __init__(self, solver):
        self.solver = solver
        self.__image_procs = []
        self.__has_display = (os.name == "posix")

    def show_image(self, image):
        oSolver = cInputWindow(captcha=image, msg= Objectif, roundnum=1)
        retArg = oSolver.get()
        if retArg == False:
            return False
        else:
            return retArg

    def run(self):
        self.solver.run()

class CliDynamicSolver(CliSolver):
    def __init__(self, solver):
        super().__init__(solver)
        solver.on_initial_image = self.handle_initial_image
        solver.on_tile_image = self.handle_tile_image
        self.image_open = False
        self.image_queue = Queue()
        self.num_pending = 0
        self.lock = RLock()

    def handle_initial_image(self, image, **kwargs):
        solver = self.solver
        indices = self.show_image(image)
        if indices == False:
            return False
        self.select_initial(indices)
        self.new_tile_loop()
        solver.finish()

    def show_imageNewTile(self, image):
        oSolver = cInputWindowYesNo(captcha=image, msg="Est-ce que cette image est en lien avec le thème ?", roundnum=1)
        retArg = oSolver.get()
        return retArg

    def new_tile_loop(self):
        while self.num_pending > 0:
            index, image = self.image_queue.get()
            self.num_pending -= 1
            accept = self.show_imageNewTile(image)[:1].lower() == "y"
            if accept:
                self.select_tile(index)

    # Called from a non-main thread.
    def handle_tile_image(self, index, image, **kwargs):
        self.image_queue.put((index, image))

    def select_initial(self, indices):
        if indices == False:
            solver = self.solver
            solver.finish()

        for i, index in enumerate(indices):
            # Avoid sending initial requests simultaneously.
            self.select_tile(index, 0.25 * i)

    def select_tile_sync(self, index):
        self.num_pending += 1
        self.solver.select_tile(index)

    def select_tile(self, index, delay=0):
        def target():
            delay and time.sleep(delay)
            with self.lock:
                self.select_tile_sync(index)
        Thread(target=target, daemon=True).start()


class CliMultiCaptchaSolver(CliSolver):
    def __init__(self, solver):
        super().__init__(solver)
        solver.on_image = self.handle_image

    def handle_image(self, image, **kwargs):
        solver = self.solver
        indices = self.show_image(image)
        if indices == False:
            return False
        solver.select_indices(indices)

BLOCKED_MSG = """\
ERROR: Received challenge type "{}".

This is usually an indication that reCAPTCHA requests from this network are
being blocked.

Try installing Tor (the full installation, not just the browser bundle) and
running this program over Tor with the "torsocks" command.

Alternatively, try waiting a while before requesting another challenge over
this network.
"""


class Cli(Frontend):
    def __init__(self, recaptcha):
        super().__init__(recaptcha)
        rc = recaptcha
        rc.on_goal = self.handle_goal
        rc.on_challenge = self.handle_challenge
        rc.on_challenge_dynamic = self.challenge_dynamic
        rc.on_challenge_multicaptcha = self.challenge_multicaptcha
        rc.on_challenge_blocked = self.challenge_blocked
        rc.on_challenge_unknown = self.challenge_unknown
        self._first = True

    def handle_goal(self, goal, meta, **kwargs):
        if goal:
            return
        global Objectif
        Objectif = json.dumps(meta).split(',')[6]

    def handle_challenge(self, ctype, **kwargs):
        if not self._first:
            VSlog("You must solve another challenge.")
        self._first = False

    def challenge_dynamic(self, solver, **kwargs):
        CliDynamicSolver(solver).run()

    def challenge_multicaptcha(self, solver, **kwargs):
        CliMultiCaptchaSolver(solver).run()

    def challenge_blocked(self, ctype, **kwargs):
        self.raise_challenge_blocked(ctype)

    def challenge_unknown(self, ctype, **kwargs):
        self.raise_challenge_unknown(ctype)

    @classmethod
    def raise_challenge_blocked(cls, ctype):
        raise UserError(
            "Error: Unsupported challenge type: {}.\n".format(ctype) +
            "Requests are most likely being blocked; see the message above.",
        )

    @classmethod
    def raise_challenge_unknown(cls, ctype):
        raise UserError(
            "Error: Got unsupported challenge type: {}\n".format(ctype) +
            "Please file an issue if this problem persists.",
        )

class cInputWindow(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.cptloc = kwargs.get('captcha')

        bg_image = 'special://home/addons/plugin.video.vstream/resources/art/background.png'
        check_image = 'special://home/addons/plugin.video.vstream/resources/art/trans_checked.png'

        self.ctrlBackground = xbmcgui.ControlImage(0, 0, 1280, 720, bg_image)
        self.cancelled = False
        self.addControl (self.ctrlBackground)

        self.strActionInfo = xbmcgui.ControlLabel(250, 20, 724, 400, 'Le thème est : ' + kwargs.get('msg'), 'font40', '0xFFFF00FF')
        self.addControl(self.strActionInfo)

        self.img = xbmcgui.ControlImage(250, 110, 780, 499, str(self.cptloc))
        self.addControl(self.img)

        self.chk = [0]*9
        self.chkbutton = [0]*9
        self.chkstate = [False]*9

        if 1 == 2:
            self.chk[0] = xbmcgui.ControlCheckMark(250, 110, 260, 166, '1', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)
            self.chk[1] = xbmcgui.ControlCheckMark(250 + 260, 110, 260, 166, '2', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)
            self.chk[2] = xbmcgui.ControlCheckMark(250 + 520, 110, 260, 166, '3', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)

            self.chk[3] = xbmcgui.ControlCheckMark(250, 110 + 166, 260, 166, '4', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)
            self.chk[4] = xbmcgui.ControlCheckMark(250 + 260, 110 + 166, 260, 166, '5', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)
            self.chk[5] = xbmcgui.ControlCheckMark(250 + 520, 110 + 166, 260, 166, '6', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)

            self.chk[6] = xbmcgui.ControlCheckMark(250, 110 + 332, 260, 166, '7', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)
            self.chk[7] = xbmcgui.ControlCheckMark(250 + 260, 110 + 332, 260, 166, '8', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)
            self.chk[8] = xbmcgui.ControlCheckMark(250 + 520, 110 + 332, 260, 166, '9', font='font14', focusTexture=check_image, checkWidth=260, checkHeight=166)

        else:
            self.chk[0] = xbmcgui.ControlImage(250, 110, 260, 166, check_image)
            self.chk[1] = xbmcgui.ControlImage(250 + 260, 110, 260, 166, check_image)
            self.chk[2] = xbmcgui.ControlImage(250 + 520, 110, 260, 166, check_image)

            self.chk[3] = xbmcgui.ControlImage(250, 110 + 166, 260, 166, check_image)
            self.chk[4] = xbmcgui.ControlImage(250 + 260, 110 + 166, 260, 166, check_image)
            self.chk[5] = xbmcgui.ControlImage(250 + 520, 110 + 166, 260, 166, check_image)

            self.chk[6] = xbmcgui.ControlImage(250, 110 + 332, 260, 166, check_image)
            self.chk[7] = xbmcgui.ControlImage(250 + 260, 110 + 332, 260, 166, check_image)
            self.chk[8] = xbmcgui.ControlImage(250 + 520, 110 + 332, 260, 166, check_image)

            self.chkbutton[0] = xbmcgui.ControlButton(250, 110, 260, 166, '1', font='font1')
            self.chkbutton[1] = xbmcgui.ControlButton(250 + 260, 110, 260, 166, '2', font='font1')
            self.chkbutton[2] = xbmcgui.ControlButton(250 + 520, 110, 260, 166, '3', font='font1')

            self.chkbutton[3] = xbmcgui.ControlButton(250, 110 + 166, 260, 166, '4', font='font1')
            self.chkbutton[4] = xbmcgui.ControlButton(250 + 260, 110 + 166, 260, 166, '5', font='font1')
            self.chkbutton[5] = xbmcgui.ControlButton(250 + 520, 110 + 166, 260, 166, '6', font='font1')

            self.chkbutton[6] = xbmcgui.ControlButton(250, 110 + 332, 260, 166, '7', font='font1')
            self.chkbutton[7] = xbmcgui.ControlButton(250 + 260, 110 + 332, 260, 166, '8', font='font1')
            self.chkbutton[8] = xbmcgui.ControlButton(250 + 520, 110 + 332, 260, 166, '9', font='font1')

        for obj in self.chk:
            self.addControl(obj)
            obj.setVisible(False)
        for obj in self.chkbutton:
            self.addControl(obj)

        self.cancelbutton = xbmcgui.ControlButton(250 + 260 - 70, 620, 140, 50, 'Cancel', alignment=2)
        self.okbutton = xbmcgui.ControlButton(250 + 520 - 50, 620, 100, 50, 'OK', alignment=2)
        self.addControl(self.okbutton)
        self.addControl(self.cancelbutton)

        self.chkbutton[6].controlDown(self.cancelbutton);  self.chkbutton[6].controlUp(self.chkbutton[3])
        self.chkbutton[7].controlDown(self.cancelbutton);  self.chkbutton[7].controlUp(self.chkbutton[4])
        self.chkbutton[8].controlDown(self.okbutton);      self.chkbutton[8].controlUp(self.chkbutton[5])

        self.chkbutton[6].controlLeft(self.chkbutton[8]);  self.chkbutton[6].controlRight(self.chkbutton[7]);
        self.chkbutton[7].controlLeft(self.chkbutton[6]);  self.chkbutton[7].controlRight(self.chkbutton[8]);
        self.chkbutton[8].controlLeft(self.chkbutton[7]);  self.chkbutton[8].controlRight(self.chkbutton[6]);

        self.chkbutton[3].controlDown(self.chkbutton[6]);  self.chkbutton[3].controlUp(self.chkbutton[0])
        self.chkbutton[4].controlDown(self.chkbutton[7]);  self.chkbutton[4].controlUp(self.chkbutton[1])
        self.chkbutton[5].controlDown(self.chkbutton[8]);  self.chkbutton[5].controlUp(self.chkbutton[2])

        self.chkbutton[3].controlLeft(self.chkbutton[5]);  self.chkbutton[3].controlRight(self.chkbutton[4]);
        self.chkbutton[4].controlLeft(self.chkbutton[3]);  self.chkbutton[4].controlRight(self.chkbutton[5]);
        self.chkbutton[5].controlLeft(self.chkbutton[4]);  self.chkbutton[5].controlRight(self.chkbutton[3]);

        self.chkbutton[0].controlDown(self.chkbutton[3]);  self.chkbutton[0].controlUp(self.cancelbutton)
        self.chkbutton[1].controlDown(self.chkbutton[4]);  self.chkbutton[1].controlUp(self.cancelbutton)
        self.chkbutton[2].controlDown(self.chkbutton[5]);  self.chkbutton[2].controlUp(self.okbutton)

        self.chkbutton[0].controlLeft(self.chkbutton[2]);  self.chkbutton[0].controlRight(self.chkbutton[1]);
        self.chkbutton[1].controlLeft(self.chkbutton[0]);  self.chkbutton[1].controlRight(self.chkbutton[2]);
        self.chkbutton[2].controlLeft(self.chkbutton[1]);  self.chkbutton[2].controlRight(self.chkbutton[0]);

        self.cancelled = False
        self.setFocus(self.okbutton)
        self.okbutton.controlLeft(self.cancelbutton);      self.okbutton.controlRight(self.cancelbutton);
        self.cancelbutton.controlLeft(self.okbutton);      self.cancelbutton.controlRight(self.okbutton);
        self.okbutton.controlDown(self.chkbutton[2]);      self.okbutton.controlUp(self.chkbutton[8]);
        self.cancelbutton.controlDown(self.chkbutton[0]);  self.cancelbutton.controlUp(self.chkbutton[6]);

    def get(self):
        self.doModal()
        self.close()
        if not self.cancelled:
            retval = []
            for objn in range(9):
                if self.chkstate[objn]:
                    retval.append(int(objn))
            return retval

        else:
            return False

    def anythingChecked(self):
        for obj in self.chkstate:
            if obj:
                return True
        return False

    def onControl(self, control):
        if str(control.getLabel()) == "OK":
            if self.anythingChecked():
                self.close()
        elif str(control.getLabel()) == "Cancel":
            self.cancelled = True
            self.close()
        try:
            if 'xbmcgui.ControlButton' in repr(type(control)):
                index = control.getLabel()
                if index.isnumeric():
                    self.chkstate[int(index)-1] = not self.chkstate[int(index)-1]
                    self.chk[int(index)-1].setVisible(self.chkstate[int(index)-1])

        except:
            pass

    def onAction(self, action):
        if action == 10:
            self.cancelled = True
            self.close()

class cInputWindowYesNo(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.cptloc = kwargs.get('captcha')

        bg_image = 'special://home/addons/plugin.video.vstream/resources/art/background.png'

        self.ctrlBackground = xbmcgui.ControlImage(0, 0, 1280, 720, bg_image)
        self.cancelled = False
        self.addControl (self.ctrlBackground)

        self.strActionInfo = xbmcgui.ControlLabel(250, 20, 724, 400, kwargs.get('msg'), 'font40', '0xFFFF00FF')
        self.addControl(self.strActionInfo)

        self.img = xbmcgui.ControlImage(250, 110, 500, 300, str(self.cptloc))
        self.addControl(self.img)

        self.Yesbutton = xbmcgui.ControlButton(250 + 520 - 50, 620, 100, 50, 'Yes', alignment=2)
        self.Nobutton = xbmcgui.ControlButton(250 + 260 - 70, 620, 140, 50, 'No', alignment=2)
        self.addControl(self.Yesbutton)
        self.addControl(self.Nobutton)

        self.setFocus(self.Yesbutton)
        self.Yesbutton.controlLeft(self.Nobutton);      self.Nobutton.controlRight(self.Yesbutton);

    def get(self):
        self.doModal()
        self.close()
        retval = self.chkstate
        return retval

    def anythingChecked(self):
        for obj in self.chkstate:
            if obj:
                return True
        return False

    def onControl(self, control):
        try:
            index = control.getLabel()
            if "Yes" in index:
                self.chkstate = "Y"
                self.chk = "Y"
            else:
                self.chkstate = "N"
                self.chk = "N"
        except:
            pass

        if str(control.getLabel()) == "Yes":
            self.close()
        elif str(control.getLabel()) == "No":
            self.close()
