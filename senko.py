import mrequests as requests
import uhashlib
import gc
import os


class Senko:
    raw = "https://raw.githubusercontent.com"
    github = "https://github.com"

    def __init__(self, url=None, branch="master", files=["boot.py", "main.py"], headers={}, debug=True, buffersize=4096, cleanup=[]):
        """Senko OTA agent class.

        Args:
            url (str): URL to root directory.
            files (list): Files to check for updates.
            headers (list, optional): Headers for requests, e.g. 'Authorization': 'token {}'.format(token)
        """
        self.url = url
        self.headers = headers
        self.files = files
        self.cleanup = cleanup
        self.debug = debug
        self.BUF_SIZE = buffersize


    def _stream_to_hash(self, stream):
        hasher = uhashlib.sha1()
        while True:
            gc.collect()
            data = stream.read(self.BUF_SIZE)
            if not data:
                break
            hasher.update(data)
        digest = hasher.digest()
        return digest

    def _compute_file_hash(self, file):
        digest = ""
        try:
            reader = open(file, 'rb')
            digest = self._stream_to_hash(reader)
            reader.close()
        except Exception as e:
            if self.debug:
                print('missing file', file, e)
        if self.debug:
            print('_compute_file_hash', file, digest)
        return digest

    def _compute_url_hash(self, url):
        hasher = uhashlib.sha1()
        r = requests.get(url, headers=self.headers)
        if r.status_code != 200:
            if self.debug:
                print('URL not loaded', url, r.status_code)
            return None

        digest = self._stream_to_hash(r)
        if self.debug:
            print('_compute_url_hash', url, digest)
        return digest

    def _stream_url_to_file(self, url, file):
        try:
            r = requests.get(url, headers=self.headers)
            if r.status_code != 200:
                if self.debug:
                    print('URL not loaded', url, r.status_code)
                return None

            with open(file, 'wb') as writer:
                # print('writer', writer)
                while True:
                    gc.collect()
                    data = r.read(self.BUF_SIZE)
                    if not data:
                        break
                    writer.write(data)
        except Exception as e:
            if self.debug:
                print('write error', url, file, e)
            return None
        if self.debug:
            print('_stream_url_to_file', file, url)


    def _check_all(self):
        changes = []

        for file in self.files:
            gc.collect()
            local_hash = self._compute_file_hash(file)
            latest_hash = self._compute_url_hash(self.url + "/" + file)

            if not str(local_hash) == str(latest_hash):
                changes.append(file)

        if self.debug:
            print("found changes", changes)
        return changes

    def fetch(self):
        """Check if newer version is available.

        Returns:
            True - if is, False - if not.
        """
        if not self._check_all():
            return False
        else:
            return True

    def update(self):
        """Replace all changed files with newer one.

        Returns:
            True - if changes were made, False - if not.
        """
        changes = self._check_all()

        for file in changes:
            gc.collect()
            if self.debug:
                print("writing to", file)
            self._stream_url_to_file(self.url + "/" + file, file)

        for file in self.cleanup:
            if self.debug:
                print("removing file", file)
            try:
                os.remove(file)
            except Exception as e:
                if self.debug:
                    print("failed to remove file", file)

        if changes:
            return True
        else:
            return False
