import threading


class StorageService(threading.Thread):
    def __init__(self, db, incoming, outgoing):
        super().__init__(daemon=True)
        self.db = db
        self.incoming = incoming
        self.outgoing = outgoing
        self.session = 0

    def run(self):
        while True:
            event = self.incoming.get()
            if event is None:
                break
            session, kind, value = event
            if session != self.session:
                continue
            if kind == "reading":
                try:
                    self.db.insert(value)
                except Exception as e:
                    self.outgoing.put(
                        (session, "notice", "Falha ao salvar leitura: " + str(e))
                    )
                    continue
            self.outgoing.put(event)
