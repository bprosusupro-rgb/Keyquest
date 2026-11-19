package org.keyquest.studio;

import android.app.Activity;
import android.content.ContentUris;
import android.content.ContentValues;
import android.content.Intent;
import android.database.Cursor;
import android.net.Uri;
import android.os.Bundle;
import android.provider.MediaStore;
import android.widget.Toast;

import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;

/** Saves a game-owned diagnostic snapshot using Studio's Android storage integration. */
public final class LogExportActivity extends Activity {
    private static final int PICK_FILE = 1;
    private byte[] log;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        String name = getIntent().getStringExtra("name");
        String text = getIntent().getStringExtra("log");
        if (name == null || !name.matches("Keyquest-[a-zA-Z0-9_.]{1,180}\\.log\\.txt")
                || text == null || text.isEmpty() || text.length() > 196608) {
            finish();
            return;
        }
        log = text.getBytes(StandardCharsets.UTF_8);
        if (log.length > 196608) {
            finish();
            return;
        }
        if (state != null && state.getBoolean("picker")) return;
        try {
            saveInDownloads(name);
            done("Saved in Downloads · " + name);
        } catch (IOException | RuntimeException blocked) {
            Intent picker = new Intent(Intent.ACTION_CREATE_DOCUMENT)
                    .addCategory(Intent.CATEGORY_OPENABLE).setType("text/plain")
                    .putExtra(Intent.EXTRA_TITLE, name);
            try {
                startActivityForResult(picker, PICK_FILE);
            } catch (RuntimeException unavailable) {
                done("Could not save to Downloads. The log is still saved in the game.");
            }
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle state) {
        super.onSaveInstanceState(state);
        state.putBoolean("picker", true);
    }

    private void saveInDownloads(String name) throws IOException {
        Uri collection = MediaStore.Downloads.EXTERNAL_CONTENT_URI;
        Uri file = null;
        try (Cursor matches = getContentResolver().query(collection, new String[]{"_id"},
                "_display_name=? AND relative_path=?",
                new String[]{name, "Download/"}, null)) {
            if (matches != null && matches.moveToFirst()) {
                file = ContentUris.withAppendedId(collection, matches.getLong(0));
            }
        }
        if (file != null) {
            write(file);
            return;
        }
        ContentValues values = new ContentValues();
        values.put(MediaStore.Downloads.DISPLAY_NAME, name);
        values.put(MediaStore.Downloads.MIME_TYPE, "text/plain");
        values.put(MediaStore.Downloads.RELATIVE_PATH, "Download/");
        values.put(MediaStore.Downloads.IS_PENDING, 1);
        file = getContentResolver().insert(collection, values);
        if (file == null) throw new IOException("Downloads entry unavailable");
        try {
            write(file);
            values.clear();
            values.put(MediaStore.Downloads.IS_PENDING, 0);
            if (getContentResolver().update(file, values, null, null) != 1) {
                throw new IOException("Could not publish the log");
            }
        } catch (IOException | RuntimeException failure) {
            getContentResolver().delete(file, null, null);
            throw failure;
        }
    }

    private void write(Uri file) throws IOException {
        try (OutputStream output = getContentResolver().openOutputStream(file, "rwt")) {
            if (output == null) throw new IOException("Log stream unavailable");
            output.write(log);
        }
    }

    @Override
    protected void onActivityResult(int request, int result, Intent data) {
        super.onActivityResult(request, result, data);
        if (request != PICK_FILE) return;
        if (result == RESULT_OK && data != null && data.getData() != null) {
            try {
                write(data.getData());
                done("Diagnostic log saved.");
                return;
            } catch (IOException | RuntimeException blocked) {
                done("Could not save the file. The log is still saved in the game.");
                return;
            }
        }
        done("Export canceled. The log is still saved in the game.");
    }

    private void done(String message) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show();
        finish();
    }
}
