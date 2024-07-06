import enum
import logging
import math
import multiprocessing
import subprocess
import sys
import queue

from pt_miniscreen.core import App
from pt_miniscreen.core import Component
from pt_miniscreen.core.components import Text

from pitop.miniscreen import Miniscreen

import find_disks
import backup

log = logging.getLogger(__name__)

dbglvl = logging.DEBUG

logging.basicConfig(level=dbglvl)

class State(enum.Enum):
  SEARCHING = 1
  BACKUP_READY = 2
  BACKUP_RUNNING = 3
  BACKUP_DONE = 4
  BACKUP_ERROR = 5
  UNMOUNTING = 6
  UNMOUNT_FAILED = 7

class BackupUI(Component):
  # define a `default_state` dictionary to create state with known values
  default_state = dict(
    st=State.SEARCHING,
    src=None,
    dst=None,
    tock=True,
    progress=0,
    exitcode=None,
    unmounting_src=False,
    unmounting_dst=False,
    unmount_count=0,
    unmount_fail_path=None,
  )

  def __init__(self, **kwargs):
    super().__init__(**kwargs)
    self.text = self.create_child(
      Text,
      text="Searching +\n\n\n\nX to exit",
      font_size=10,
      align="left",
      vertical_align="top",
      wrap=False,
    )
    self._tick_interval = self.create_interval(self.tick, timeout=1)
    self._queue = None
    self._proc = None

    # Hit log level with a stick.  I think something in the minscreen
    # framework resets it.
    logging.getLogger().setLevel(dbglvl)  

  def select_button_pressed(self):
    if self.state["st"] == State.BACKUP_READY:
      self.select_in_backup_ready()
    elif self.state["st"] == State.BACKUP_DONE:
      self.select_in_backup_done()

  def select_in_backup_ready(self):
    self.start_backup()
    self.update_text()

  def select_in_backup_done(self):
    self.state.update(st=State.UNMOUNTING, unmounting_src=True)
    self.update_text()
          
  def start_backup(self):
    assert self._queue is None
    assert self._proc is None
    self._queue = multiprocessing.Queue(100)

    src = self.state["src"]
    dst, tgt = backup.make_target_directory(self.state["dst"])

    log.info("Starting Backup from : %r to %r", src, dst)
    
    # Start the process
    self._proc = multiprocessing.Process(target=backup.backup_proc,
                                         args=(src, dst, self._queue))
    self._proc.start()
    self.state.update(st=State.BACKUP_RUNNING, dst=dst, progress=0)

  def tick(self):
    log.debug("tick")
    
    self.state.update(tock=not self.state["tock"])
    if self.state["st"] == State.SEARCHING:
      self.tick_in_searching()
    elif self.state["st"] == State.BACKUP_RUNNING:
      self.tick_in_backup_running()
    elif self.state["st"] == State.UNMOUNTING:
      self.tick_in_unmount()
    self.update_text()

  def tick_in_searching(self):
    res = find_disks.find_disks()
    log.info("Found Disks: %s", res)
    if res.backup_a is not None and res.cf_card is not None:
      self.state.update(st=State.BACKUP_READY,
                        src=res.cf_card,
                        dst=res.backup_a)

  def tick_in_backup_running(self):
    drain = True
    while drain:
      # Get message tuples from the q.  Don't block if the queue
      # is empty.
      try:
        t = self._queue.get_nowait()
        if t[0] == 'C':
          pass
        elif t[0] == 'B':
          self.state.update(progress=t[2] / t[1])
        else:
          log.warning("Unknown message: %r", t)
      except queue.Empty:
        drain = False

      # Try to join the process, but don't block.
      self._proc.join(0)

      if self._proc.exitcode is not None:
        # The process exited
        log.info("Child exited: %d", self._proc.exitcode)
        if self._proc.exitcode == 0:
          self.state.update(st=State.BACKUP_DONE, exitcode=0)
        else:
          self.state.update(st=State.BACKUP_ERROR, exitcode=self._proc.exitcode)
        self._queue.close()
        self._queue = None
        self._proc.close()
        self._proc = None


  def get_disks_to_unmount(self) -> [str]:
    ret = []
    fd = find_disks.find_disks()
    
    if self.state["unmounting_src"]:
      if fd.cf_card:
        ret.append(fd.cf_card)
    if self.state["unmounting_dst"]:
      if fd.backup_a:
        ret.append(fd.backup_a)

    return ret
    
  def tick_in_unmount(self):
    # We try to unmount repeatedly, because on Pi-Top, when a disk
    # that has previously been mounted by the 'pi' user is unmounted,
    # it gets remounted by root, which is just annoying.  So we try 5
    # times over 5 seconds.

    disks = self.get_disks_to_unmount()
    
    log.info("Found disks while unmounting: %r", disks)

    if self.state['unmount_count'] > 5:
      if len(disks) > 0:
        self.state.update(st=State.UNMOUNT_FAILED, unmount_fail_path=disks)
      else:
        # Success
        self.state.update(**self.default_state) # Reset state
      return

    for path in disks:
      self.do_unmount(path)

    self.state.update(unmount_count=self.state['unmount_count'] + 1)

  def do_unmount(self, path):
    log.info("Unmounting: %s", path)
    proc = subprocess.run(["/usr/bin/sudo", "/usr/bin/umount", path], stderr=subprocess.STDOUT)
    if proc.returncode == 0:
      # SUCCESS
      log.info("Unmount successful")
    else:
      log.error("Unmount of %s failed: %d \"%s\"", path, proc.returncode, proc.stdout)

  def update_text(self):
    def ticker():
      return "*" if self.state["tock"] else "+"

    text = "NONE"

    st = self.state["st"] 
    
    if st == State.SEARCHING:
      text = f"Searching {ticker()}\n\n\n\nX to Exit"
    elif st == State.BACKUP_READY:
      text = f"Ready\nS: {self.state['src']}\nD: {self.state['dst']}\n\nO to start, X to Exit"
    elif st == State.BACKUP_RUNNING:
      p = math.ceil(self.state['progress'] * 100)
      text = f"Running {ticker()}\nS: {self.state['src']}\nD: {self.state['dst']}\nP: {p}%\nX to Exit"
    elif st == State.BACKUP_DONE:
      text = f"Complete\n\n\n\nO to Unmount CF, X to Exit" # TODO: stats
    elif st == State.BACKUP_ERROR:
      text = f"Backup Failed\nE: {self.state['exitcode']}\n\n\nX to Exit"
    elif st == State.UNMOUNTING:
      disks = "\n".join(self.get_disks_to_unmount())
      text = f"Unmounting {ticker()}\n{disks}"
    elif st == State.UNMOUNT_FAILED:
      text = f"Failed to unmount\n {self.state['unmount_fail_path']}"

    self.text.state.update(text=text)
    
  def render(self, image):
      return self.text.render(image)
    
class BackupApp(App):
  def __init__(self, miniscreen):
    super().__init__(display=miniscreen.device.display, Root=BackupUI)

    # We call methods on self, because self.root does not exist until
    # start() is run. So if we said `self.root.button_pressed` we'd
    # get an exception.
    miniscreen.select_button.when_pressed = self.select_button_pressed
    miniscreen.cancel_button.when_pressed = self.cancel_button_pressed

  def select_button_pressed(self):
    self.root.select_button_pressed()

  def cancel_button_pressed(self):
    self.stop()

def main():
  m = Miniscreen()

  a = BackupApp(m)
  
  a.start()
  a.wait_for_stop()

if __name__ == '__main__':
  main()

