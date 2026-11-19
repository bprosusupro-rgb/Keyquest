# Local recognition in the game process. Only screenshot capture touches Ren'Py's renderer.

init python:
    def _keyquest_ocr_crop(width, height, region):
        if min(width, height) < 8:
            return None
        if region == "top":
            return (0, 0, width, height // 3)
        if region == "center":
            return (width // 10, height // 4, width * 4 // 5, height // 2)
        if region == "bottom":
            return (width // 5, height * 17 // 25, width * 3 // 5, height // 4)
        if region == "typing":
            return (width // 50, height * 3 // 5, width * 24 // 25, height * 39 // 100)
        if region == "race":
            return (width * 23 // 100, height // 8, width * 54 // 100, height * 3 // 16)
        return None

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
            self.set_variable = bind(tess, "TessBaseAPISetVariable", integer, pointer, c.c_char_p, c.c_char_p)
            self.clear = bind(tess, "TessBaseAPIClear", None, pointer)
            self.read_png = bind(lept, "pixReadMemPng", pointer, c.c_char_p, c.c_size_t)
            self.width = bind(lept, "pixGetWidth", integer, pointer)
            self.height = bind(lept, "pixGetHeight", integer, pointer)
            self.box = bind(lept, "boxCreate", pointer, integer, integer, integer, integer)
            self.crop = bind(lept, "pixClipRectangle", pointer, pointer, pointer, pointer)
            self.release_box = bind(lept, "boxDestroy", None, c.POINTER(pointer))
            self.rgb = bind(lept, "pixConvertTo32", pointer, pointer)
            self.brightness = bind(lept, "pixConvertRGBToGrayMinMax", pointer, pointer, integer)
            self.luminance = bind(lept, "pixConvertRGBToLuminance", pointer, pointer)
            self.invert = bind(lept, "pixInvert", pointer, pointer, pointer)
            self.threshold = bind(lept, "pixThresholdToBinary", pointer, pointer, integer)
            self.release_image = bind(lept, "pixDestroy", None, c.POINTER(pointer))
            self.engine = create()
            if not self.engine:
                raise RuntimeError("Could not create OCR engine")
            path = model_directory.encode("utf-8") if not isinstance(model_directory, bytes) else model_directory
            if initialize(self.engine, path, b"eng") != 0:
                self.delete(self.engine)
                raise RuntimeError("Could not initialize OCR model")

        def recognize(self, frame, region, mode, validate=None):
            image = self.read_png(frame, len(frame))
            if not image:
                raise ValueError("Could not decode game frame")
            cropped = None
            filtered = None
            digits = mode.startswith("digits")
            try:
                width, height = self.width(image), self.height(image)
                area = _keyquest_ocr_crop(width, height, region)
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
                source = cropped or image
                race = region == "race" and mode == "keys"
                if digits:
                    self.set_variable(self.engine, b"tessedit_char_whitelist", b"0123456789")
                    if mode != "digits":
                        filtered = self.tile_label_mask(source)
                if race:
                    passes = ((7, 100), (7, 145), (7, None))
                elif digits:
                    passes = ((7 if mode == "digits-light" else 8, None),)
                elif mode == "math" and region == "bottom":
                    passes = ((11, None), (7, None))
                elif mode != "text":
                    passes = ((11, None),)
                else:
                    passes = ((6 if region == "typing" else 3, None), (11, None))
                for segmentation, threshold in passes:
                    if threshold is not None:
                        if filtered:
                            self.release_image(self.ctypes.byref(self.ctypes.c_void_p(filtered)))
                        filtered = self.race_text_mask(source, threshold)
                    self.mode(self.engine, segmentation)
                    self.set_image(self.engine, (filtered if digits or threshold is not None else None) or source)
                    text = self.text(self.engine)
                    if text:
                        try:
                            result = self.ctypes.string_at(text).decode("utf-8", "replace").strip()[:4096]
                        finally:
                            self.release_text(text)
                        if result and (validate is None or validate(result)):
                            return result
                return u""
            finally:
                self.clear(self.engine)
                if digits:
                    self.set_variable(self.engine, b"tessedit_char_whitelist", b"")
                for pix in (filtered, cropped, image):
                    if pix:
                        self.release_image(self.ctypes.byref(self.ctypes.c_void_p(pix)))

        def tile_label_mask(self, image):
            rgb = self.rgb(image)
            if not rgb:
                return None
            gray = None
            try:
                gray = self.luminance(rgb)
                mask = self.threshold(gray, 190) if gray else None
                if mask:
                    self.invert(mask, mask)
                return mask
            finally:
                for pix in (gray, rgb):
                    if pix:
                        self.release_image(self.ctypes.byref(self.ctypes.c_void_p(pix)))

        def race_text_mask(self, image, threshold):
            rgb = self.rgb(image)
            if not rgb:
                return None
            gray = None
            try:
                # Keep the dark letter outlines and suppress the saturated track and white stripes.
                gray = self.brightness(rgb, 2)  # L_CHOOSE_MAX
                return self.threshold(gray, threshold) if gray else None
            finally:
                for pix in (gray, rgb):
                    if pix:
                        self.release_image(self.ctypes.byref(self.ctypes.c_void_p(pix)))

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

        def start(self, request, frame, region, mode, root, validate=None):
            import threading

            if self.busy:
                return False
            self.response = None
            self.busy = True

            def scan():
                try:
                    if self.engine is None:
                        self.prepare(root)
                    text = self.engine.recognize(frame, region, mode, validate)
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
