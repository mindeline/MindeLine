package app.mindeline.mobile;

import android.content.Intent;
import android.os.Bundle;
import com.google.androidbrowserhelper.trusted.LauncherActivity;

/** Opens only the configured MindeLine origin. No patient IDs, tokens or incoming URLs forwarded. */
public class MobileActivity extends LauncherActivity {
    @Override
    protected void onCreate(Bundle state) {
        // Discard untrusted Intent data/extras before Browser Helper selects a launch URL.
        setIntent(new Intent(this, MobileActivity.class));
        super.onCreate(state);
    }
}
