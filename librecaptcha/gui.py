import xbmcaddon
import xbmcvfs
import xbmcgui

from resources.lib.comaddon import VSlog

class cInputWindow(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.cptloc = kwargs.get('captcha')
        
        DimTab = kwargs.get('dimtab')
        DimTab = [3,3]
        
        bg_image = 'special://home/addons/plugin.video.vstream/resources/art/background.png'
        check_image = 'special://home/addons/plugin.video.vstream/resources/art/trans_checked.png'

        self.ctrlBackground = xbmcgui.ControlImage(0, 0, 1280, 720, bg_image)
        self.cancelled = False
        self.addControl (self.ctrlBackground)

        self.strActionInfo = xbmcgui.ControlLabel(250, 20, 724, 400, 'Le thème est : ' + kwargs.get('msg'), 'font40', '0xFFFF00FF')
        self.addControl(self.strActionInfo)

        self.img = xbmcgui.ControlImage(250, 110, 780, 499, str(self.cptloc))
        self.addControl(self.img)

        self.chk = [0] * DimTab[0] * DimTab[1]
        self.chkbutton = [0] * DimTab[0] * DimTab[1]
        self.chkstate = [False] * DimTab[0] * DimTab[1]
        
        c = 0
        cx = int(780 / DimTab[0]) #260
        cy = int(498 / DimTab[1]) #166
        
        for x in range(DimTab[0]):
            for y in range(DimTab[1]):

                self.chk[c] = xbmcgui.ControlImage(250 + cx * x, 110 + cy * y, 260, 166, check_image)
                self.chkbutton[c] = xbmcgui.ControlButton(250 + cx * x, 110 + cy * y, 260, 166, str(c + 1), font='font1')
                c += 1

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
