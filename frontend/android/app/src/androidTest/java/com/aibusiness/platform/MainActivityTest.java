package com.aibusiness.platform;

import android.content.Context;
import androidx.test.core.app.ApplicationProvider;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import androidx.test.platform.app.InstrumentationRegistry;
import org.junit.Test;
import org.junit.runner.RunWith;
import static org.junit.Assert.*;

/**
 * MOB-P2-004: Basic instrumented tests for Android.
 * Run with: cd android && gradlew connectedAndroidTest
 */
@RunWith(AndroidJUnit4.class)
public class MainActivityTest {

    @Test
    public void appContextHasCorrectPackageName() {
        Context appContext = InstrumentationRegistry.getInstrumentation().getTargetContext();
        assertEquals("com.aibusiness.platform", appContext.getPackageName());
    }

    @Test
    public void appContextIsNotNull() {
        Context appContext = ApplicationProvider.getApplicationContext();
        assertNotNull(appContext);
    }
}
