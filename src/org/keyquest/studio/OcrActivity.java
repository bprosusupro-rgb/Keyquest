package org.keyquest.studio;

import android.app.Activity;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Build;
import android.os.Bundle;
import android.os.Message;
import android.os.Messenger;
import android.os.RemoteException;

import com.googlecode.tesseract.android.TessBaseAPI;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/** Processes a single game frame and returns the text to the requesting game. */
public final class OcrActivity extends Activity {
    private static final int MAX_IMAGE_BYTES = 400 * 1024;
    private static final int MAX_PIXELS = 1_600_000;
    private static final ExecutorService WORKER = Executors.newSingleThreadExecutor();
    private static final AtomicBoolean BUSY = new AtomicBoolean();

    @Override
    @SuppressWarnings("deprecation")
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        final Messenger reply;
        final byte[] image;
        final boolean math;
        final boolean race;
        final boolean typing;
        try {
            reply = Build.VERSION.SDK_INT >= 33
                    ? getIntent().getParcelableExtra("reply", Messenger.class)
                    : getIntent().getParcelableExtra("reply");
            image = getIntent().getByteArrayExtra("image");
            math = getIntent().getBooleanExtra("math", false);
            race = getIntent().getBooleanExtra("race", false);
            typing = getIntent().getBooleanExtra("typing", false);
            getIntent().replaceExtras((Bundle) null);
        } catch (RuntimeException badExtras) {
            finish();
            return;
        }
        if (reply == null || image == null || image.length == 0 || image.length > MAX_IMAGE_BYTES) {
            finish();
            return;
        }
        if (!BUSY.compareAndSet(false, true)) {
            complete(reply, null, "OCR is busy. Try again in a moment.");
            return;
        }
        WORKER.execute(() -> {
            String result = null;
            String error = null;
            try {
                result = recognize(image, math, race, typing);
            } catch (IOException | RuntimeException | LinkageError failure) {
                android.util.Log.e("KeyquestOCR", "OCR could not process the supplied frame", failure);
                error = "OCR could not read this frame.";
            } finally {
                BUSY.set(false);
            }
            final String text = result;
            final String problem = error;
            runOnUiThread(() -> complete(reply, text, problem));
        });
    }

    private String recognize(byte[] image, boolean math, boolean race, boolean typing) throws IOException {
        BitmapFactory.Options bounds = new BitmapFactory.Options();
        bounds.inJustDecodeBounds = true;
        BitmapFactory.decodeByteArray(image, 0, image.length, bounds);
        if (bounds.outWidth <= 0 || bounds.outHeight <= 0
                || (long) bounds.outWidth * bounds.outHeight > MAX_PIXELS
                || !("image/png".equals(bounds.outMimeType) || "image/jpeg".equals(bounds.outMimeType))) {
            throw new IOException("Invalid frame");
        }

        Bitmap bitmap = BitmapFactory.decodeByteArray(image, 0, image.length);
        if (bitmap == null) throw new IOException("Frame could not be decoded");
        Bitmap source = bitmap;
        try {
            if (race) source = raceTextMask(bitmap);
            TessBaseAPI engine = new TessBaseAPI();
            try {
                if (!engine.init(languageData().getAbsolutePath(), "eng")) {
                    throw new IOException("Tesseract could not load English language data");
                }
                int segmentation = TessBaseAPI.PageSegMode.PSM_AUTO;
                if (race) segmentation = TessBaseAPI.PageSegMode.PSM_SINGLE_LINE;
                else if (typing) segmentation = TessBaseAPI.PageSegMode.PSM_SINGLE_BLOCK;
                else if (math) segmentation = TessBaseAPI.PageSegMode.PSM_SPARSE_TEXT;
                engine.setPageSegMode(segmentation);
                engine.setImage(source);
                String text = engine.getUTF8Text();
                return text == null ? "" : text.substring(0, Math.min(text.length(), 4096)).trim();
            } finally {
                engine.recycle();
            }
        } finally {
            if (source != bitmap) source.recycle();
            bitmap.recycle();
        }
    }

    private static Bitmap raceTextMask(Bitmap image) {
        int width = image.getWidth();
        int height = image.getHeight();
        int[] pixels = new int[width * height];
        image.getPixels(pixels, 0, width, 0, 0, width, height);
        for (int i = 0; i < pixels.length; i++) {
            int color = pixels[i];
            int red = (color >>> 16) & 255;
            int green = (color >>> 8) & 255;
            int blue = color & 255;
            pixels[i] = Math.max(red, Math.max(green, blue)) < 100 ? 0xff000000 : 0xffffffff;
        }
        return Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888);
    }

    private File languageData() throws IOException {
        File root = new File(getFilesDir(), "ocr-v1");
        File directory = new File(root, "tessdata");
        File language = new File(directory, "eng.traineddata");
        if (language.isFile()) return root;
        if (!directory.isDirectory() && !directory.mkdirs()) throw new IOException("Cannot create tessdata");
        File partial = File.createTempFile("language", ".tmp", directory);
        try (InputStream source = getAssets().open("ocr/eng.traineddata")) {
            Files.copy(source, partial.toPath(), StandardCopyOption.REPLACE_EXISTING);
            Files.move(partial.toPath(), language.toPath(), StandardCopyOption.ATOMIC_MOVE);
        } finally {
            Files.deleteIfExists(partial.toPath());
        }
        return root;
    }

    private void complete(Messenger reply, String text, String error) {
        finish();
        Message message = Message.obtain();
        Bundle response = new Bundle();
        response.putString("text", text);
        response.putString("error", error);
        message.setData(response);
        try {
            reply.send(message);
        } catch (RemoteException gameClosed) {
            // The game can close while recognition is in progress.
        }
    }
}
