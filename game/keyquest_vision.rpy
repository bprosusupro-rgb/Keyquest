# Local recognition in the game process. Only screenshot capture touches Ren'Py's renderer.

init python:
    class _KeyquestVisionEngine(object):
        def __init__(self, tess, lept, model_directory):
            import ctypes as c

            self.ctypes = c
            pointer, integer = c.c_void_p, c.c_int

            def bind(library, name, result, *arguments):
                function = getattr(library, name)
                function.restype = result
                function.argtypes = arguments
                return function

            create = bind(tess, "TessBaseAPICreate", pointer)
            initialize = bind(tess, "TessBaseAPIInit3", integer, pointer, c.c_char_p, c.c_char_p)
            self.delete = bind(tess, "TessBaseAPIDelete", None, pointer)
            self.mode = bind(tess, "TessBaseAPISetPageSegMode", None, pointer, integer)
            self.set_image = bind(tess, "TessBaseAPISetImage2", None, pointer, pointer)
            self.text = bind(tess, "TessBaseAPIGetUTF8Text", pointer, pointer)
            self.release_text = bind(tess, "TessDeleteText", None, pointer)
            self.clear = bind(tess, "TessBaseAPIClear", None, pointer)
            self.read_png = bind(lept, "pixReadMemPng", pointer, c.c_char_p, c.c_size_t)
            self.width = bind(lept, "pixGetWidth", integer, pointer)
            self.height = bind(lept, "pixGetHeight", integer, pointer)
            self.box = bind(lept, "boxCreate", pointer, integer, integer, integer, integer)
            self.crop = bind(lept, "pixClipRectangle", pointer, pointer, pointer, pointer)
            self.release_box = bind(lept, "boxDestroy", None, c.POINTER(pointer))
            self.release_image = bind(lept, "pixDestroy", None, c.POINTER(pointer))
            self.engine = create()
            if not self.engine:
                raise RuntimeError("Could not create OCR engine")
            path = model_directory.encode("utf-8") if not isinstance(model_directory, bytes) else model_directory
            if initialize(self.engine, path, b"eng") != 0:
                self.delete(self.engine)
                raise RuntimeError("Could not initialize OCR model")

        def recognize(self, frame, region, mode):
            image = self.read_png(frame, len(frame))
            if not image:
                raise ValueError("Could not decode game frame")
            cropped = None
            try:
                width, height = self.width(image), self.height(image)
                area = None
                if region == "top" and height >= 3:
                    area = (0, 0, width, height // 3)
                elif region == "center" and width >= 5 and height >= 5:
                    area = (width // 10, height // 4, width * 4 // 5, height // 2)
                if area is not None:
                    box = self.box(*area)
                    if not box:
                        raise ValueError("Could not select OCR region")
                    try:
                        cropped = self.crop(image, box, None)
                    finally:
                        self.release_box(self.ctypes.byref(self.ctypes.c_void_p(box)))
                    if not cropped:
                        raise ValueError("Could not crop game frame")
                self.mode(self.engine, 3 if mode == "text" else 11)
                self.set_image(self.engine, cropped or image)
                text = self.text(self.engine)
                if not text:
                    return u""
                try:
                    return self.ctypes.string_at(text).decode("utf-8", "replace").strip()[:4096]
                finally:
                    self.release_text(text)
            finally:
                self.clear(self.engine)
                if cropped:
                    self.release_image(self.ctypes.byref(self.ctypes.c_void_p(cropped)))
                self.release_image(self.ctypes.byref(self.ctypes.c_void_p(image)))

    class _KeyquestVisionWorker(object):
        engine = None
        libraries = ()
        busy = False
        unavailable = False
        response = None

        def prepare(self, root):
            import ctypes
            import io
            import os
            import shutil
            import tempfile
            import zipfile

            # Version the cache so an APK update can replace the bundled model.
            target = os.path.join(root, "keyquest-vision-v1")
            ordered = ("libjpeg.so", "libpngx.so", "libleptonica.so", "libtesseract.so")
            if not os.path.isdir(target):
                partial = tempfile.mkdtemp(prefix="keyquest-vision-", dir=root)
                try:
                    with renpy.open_file("keyquest_vision.zip") as source:
                        data = source.read()
                    with zipfile.ZipFile(io.BytesIO(data)) as archive:
                        for name in ordered + ("eng.traineddata",):
                            with open(os.path.join(partial, name), "wb") as output:
                                output.write(archive.read(name))
                    os.rename(partial, target)
                finally:
                    if os.path.isdir(partial):
                        shutil.rmtree(partial)
            self.libraries = tuple(ctypes.CDLL(os.path.join(target, name), mode=ctypes.RTLD_GLOBAL) for name in ordered)
            self.engine = _KeyquestVisionEngine(self.libraries[3], self.libraries[2], target)

        def start(self, request, frame, region, mode, root):
            import threading

            if self.busy:
                return False
            self.response = None
            self.busy = True

            def scan():
                try:
                    if self.engine is None:
                        self.prepare(root)
                    text = self.engine.recognize(frame, region, mode)
                    self.response = (request, text, None)
                except Exception as error:
                    self.unavailable = True
                    self.response = (request, None, repr(error))
                finally:
                    self.busy = False

            worker = threading.Thread(target=scan, name="Keyquest OCR")
            worker.daemon = True
            try:
                worker.start()
            except Exception:
                self.busy = False
                raise
            return True

    _keyquest_vision = _KeyquestVisionWorker()
