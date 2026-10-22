"""Contextual voice entry using Poetree's existing dictation and submit path."""
import re
import time
from plant_poem import tokenize


def phrase(text):
    return " ".join(re.sub(r"[^a-z ]", " ", text.casefold()).split())


def plant_type(text):
    value=phrase(text)
    for prefix in ("i want to plant a ","i want a ","plant a ","a "):
        if value.startswith(prefix):
            value=value[len(prefix):]
            break
    return {"flower":"flower","tree":"conifer","conifer":"conifer","fern":"fern"}.get(value)


def command(text):
    value=phrase(text)
    if value in ("confirm","yes","yes please","save","plant it","water","submit"):
        return "confirm"
    if value in ("retry","try again","again","redo","no"):
        return "retry"
    if value in ("cancel","cancel it","discard"):
        return "cancel"
    if value in ("change type","change plant"):
        return "type"
    return None


class VoiceFlow:
    DURATIONS={"type":4,"words":7,"confirm":4}
    PROMPTS={"type":"Say: flower, tree, or fern",
             "words":"Say 1-5 words for this plant",
             "confirm":"Say: confirm, retry, or cancel"}

    def __init__(self,app):
        self.app=app
        self.phase="idle"
        self.pending=False
        self.ticket=None
        self.target=None
        self.failures=0
        self.ready_at=0.

    @property
    def active(self):
        return self.phase!="idle"

    @property
    def prompt(self):
        if self.phase=="error":
            return "Voice paused. Pinch to retry here."
        if self.pending:
            return "Wait for Listening before speaking"
        return self.PROMPTS.get(self.phase,"Pinch a plant or an empty spot")

    def schedule(self,phase,delay=0.):
        self.phase=phase
        self.pending=True
        self.ticket=None
        self.ready_at=time.monotonic()+delay
        self.app.status=self.PROMPTS[phase]+". Listening starts shortly."

    def begin(self):
        self.target=(self.app.selected,self.app.pending)
        self.failures=0
        self.schedule("words" if self.app.selected else "type")

    def retry_click(self):
        if self.phase=="error":
            self.failures=0
            self.schedule(self.retry_phase)
        else:
            self.app.status=self.prompt+". Finish this voice entry before choosing another spot."

    def poll(self):
        if not self.active:
            return
        if self.app.finished or (self.app.selected,self.app.pending)!=self.target:
            self.cancel(clear=False)
            return
        if self.pending and not self.app.dictation.busy and time.monotonic()>=self.ready_at:
            self.pending=False
            self.app.speech.stop()
            self.app.status="Listening: "+self.PROMPTS[self.phase]
            self.app.dictation.start(seconds=self.DURATIONS[self.phase])
            self.ticket=self.app.dictation.ticket

    def cancel(self,clear=False):
        self.app.dictation.cancel()
        self.phase="idle"
        self.pending=False
        self.ticket=None
        if clear:
            self.app.draft=""
            self.app.caret=0
            self.app.select_all=False
            self.app.selected=self.app.pending=None
            self.app.status="Cancelled. Pinch a new spot or plant to begin."

    def submitted(self):
        failed="failed" in self.app.status.casefold()
        self.cancel(clear=False)
        if not failed:
            self.app.status="Contribution saved. Pinch a spot or plant for the next entry."

    def fail(self,message):
        self.failures+=1
        if self.failures>=3:
            self.retry_phase=self.phase
            self.phase="error"
            self.pending=False
            self.ticket=None
            self.app.status=message+". Voice paused; pinch to retry this same target."
        else:
            phase=self.phase
            self.schedule(phase,delay=1.2)
            self.app.status=message+". Retrying: "+self.PROMPTS[phase]

    def receive(self,ticket,text=None,error=None):
        if not self.active or ticket!=self.ticket:
            return False
        if self.app.finished or (self.app.selected,self.app.pending)!=self.target:
            self.cancel(clear=False)
            return True
        self.ticket=None
        if error is not None:
            self.fail("Could not hear/transcribe: "+str(error))
            return True
        if self.phase=="type":
            if command(text)=="cancel":
                self.cancel(clear=True)
                return True
            kind=plant_type(text)
            if kind is None:
                self.fail("Choose flower, tree, or fern")
                return True
            self.app.kind=kind
            self.failures=0
            self.schedule("words",delay=.7)
        elif self.phase=="words":
            text=text.strip()
            try:
                tokenize(text)
            except ValueError as exc:
                self.fail(str(exc))
                return True
            self.app.draft=text
            self.app.caret=len(text)
            self.app.select_all=False
            self.failures=0
            self.schedule("confirm",delay=1.5)
            self.app.status=f'Heard: "{text}". Review; wait for Listening, then confirm, retry, or cancel.'
        elif self.phase=="confirm":
            action=command(text)
            if action=="confirm":
                before=len(self.app.garden.history)
                self.app.action("water")
                if len(self.app.garden.history)==before:
                    self.fail("Submission was not accepted: "+self.app.status)
            elif action=="cancel":
                self.cancel(clear=True)
            elif action=="retry" or (action=="type" and self.app.pending is not None):
                self.app.draft=""
                self.app.caret=0
                self.app.select_all=False
                self.failures=0
                self.schedule("type" if action=="type" else "words",delay=.7)
            else:
                self.fail("Say only confirm, retry, or cancel")
        return True
