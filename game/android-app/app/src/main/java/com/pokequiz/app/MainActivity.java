package com.pokequiz.app;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.view.View;
import android.view.ViewGroup;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.widget.FrameLayout;

import java.util.Locale;

/**
 * Full-screen WebView that loads the self-contained Pokemon Quiz player
 * (HTML + emulator + ROM) bundled in assets. No internet permission is declared,
 * so the app is fully offline.
 *
 * A WebChromeClient is attached so the in-page controls actually work inside a
 * WebView: the "Open ROM" file picker (onShowFileChooser) and HTML fullscreen
 * (onShowCustomView). A small native TextToSpeech bridge is exposed to the page
 * as window.AndroidTTS so the "Read aloud" feature has reliable voices (the
 * WebView's own speechSynthesis often has none).
 */
public class MainActivity extends Activity {

    private static final int FILE_CHOOSER_REQUEST = 1001;

    private WebView web;
    private ValueCallback<Uri[]> filePathCallback;

    // HTML5 fullscreen (onShowCustomView) support.
    private View customView;
    private WebChromeClient.CustomViewCallback customViewCallback;

    // Native text-to-speech, exposed to the page as window.AndroidTTS.
    private TextToSpeech tts;
    private boolean ttsReady = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Keep the screen on while playing.
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);

        tts = new TextToSpeech(this, new TextToSpeech.OnInitListener() {
            @Override
            public void onInit(int status) {
                if (status == TextToSpeech.SUCCESS) {
                    tts.setLanguage(Locale.US);
                    ttsReady = true;
                }
            }
        });

        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);          // emulator is JS/WASM
        s.setDomStorageEnabled(true);          // localStorage (filter/speed/voice prefs)
        s.setMediaPlaybackRequiresUserGesture(false); // allow sound to start
        s.setAllowFileAccess(true);
        web.setBackgroundColor(0xFF06141C);

        web.setWebChromeClient(new WebChromeClient() {
            // Makes the in-page "Open ROM" file input work.
            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> cb,
                                             FileChooserParams params) {
                if (filePathCallback != null) {
                    filePathCallback.onReceiveValue(null);
                }
                filePathCallback = cb;
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                try {
                    startActivityForResult(
                            Intent.createChooser(intent, "Select a ROM (.gb / .gbc)"),
                            FILE_CHOOSER_REQUEST);
                } catch (Exception e) {
                    filePathCallback = null;
                    return false;
                }
                return true;
            }

            // Makes the in-page "Fullscreen" button work.
            @Override
            public void onShowCustomView(View view, CustomViewCallback callback) {
                if (customView != null) {
                    callback.onCustomViewHidden();
                    return;
                }
                customView = view;
                customViewCallback = callback;
                ((FrameLayout) getWindow().getDecorView()).addView(
                        customView,
                        new FrameLayout.LayoutParams(
                                ViewGroup.LayoutParams.MATCH_PARENT,
                                ViewGroup.LayoutParams.MATCH_PARENT));
                hideSystemBars();
            }

            @Override
            public void onHideCustomView() {
                exitFullscreen();
            }
        });

        web.addJavascriptInterface(new TtsBridge(), "AndroidTTS");

        setContentView(web);
        hideSystemBars();

        web.loadUrl("file:///android_asset/PokemonQuiz.html");
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_REQUEST) {
            Uri[] result = null;
            if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                result = new Uri[] { data.getData() };
            }
            if (filePathCallback != null) {
                filePathCallback.onReceiveValue(result);
                filePathCallback = null;
            }
            return;
        }
        super.onActivityResult(requestCode, resultCode, data);
    }

    @Override
    public void onBackPressed() {
        // Exit HTML fullscreen first; otherwise leave the app as usual.
        if (customView != null) {
            exitFullscreen();
            return;
        }
        super.onBackPressed();
    }

    private void exitFullscreen() {
        if (customView == null) return;
        ((FrameLayout) getWindow().getDecorView()).removeView(customView);
        customView = null;
        if (customViewCallback != null) {
            customViewCallback.onCustomViewHidden();
            customViewCallback = null;
        }
        hideSystemBars();
    }

    /** Exposed to the page as window.AndroidTTS.{speak,stop}. */
    private class TtsBridge {
        @JavascriptInterface
        public void speak(String text, float pitch, float rate) {
            if (!ttsReady || text == null || text.length() == 0) return;
            tts.setPitch(pitch);
            tts.setSpeechRate(rate);
            // QUEUE_ADD so consecutive sentences play in order rather than cutting
            // each other off; stop() (read toggled off) still clears the queue.
            tts.speak(text, TextToSpeech.QUEUE_ADD, null, "pq");
        }

        @JavascriptInterface
        public void stop() {
            if (ttsReady) tts.stop();
        }
    }

    private void hideSystemBars() {
        View d = getWindow().getDecorView();
        d.setSystemUiVisibility(
                View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
              | View.SYSTEM_UI_FLAG_FULLSCREEN
              | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
              | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
              | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION);
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) hideSystemBars();
    }

    @Override
    protected void onPause() {
        super.onPause();
        if (web != null) web.onPause();
        if (tts != null) tts.stop();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (web != null) web.onResume();
    }

    @Override
    protected void onDestroy() {
        if (tts != null) {
            tts.stop();
            tts.shutdown();
            tts = null;
        }
        super.onDestroy();
    }
}
