package io.github.godofecht.commonground

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView

/**
 * Thin Android companion for the hosted CommonGround service.
 * Google OAuth opens in the system browser to avoid embedded WebView OAuth restrictions.
 */
class MainActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var address: EditText
    private val prefs by lazy { getSharedPreferences("common_ground", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(20, 20, 20, 12)
        }
        val heading = TextView(this).apply {
            text = "CommonGround · Phone Companion"
            textSize = 19f
        }
        address = EditText(this).apply {
            hint = "https://your-commonground-server.example"
            setSingleLine(true)
            setText(prefs.getString("url", ""))
        }
        val connect = Button(this).apply {
            text = "Open companion in browser"
            setOnClickListener { openCompanion() }
        }
        val help = TextView(this).apply {
            text = "Enter the HTTPS URL of your deployed CommonGround server. " +
                "Google sign-in opens in your browser. A server is required for shared rooms and Roku pairing."
            textSize = 13f
        }
        web = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            webChromeClient = WebChromeClient()
            webViewClient = object : WebViewClient() {
                override fun shouldOverrideUrlLoading(
                    view: WebView,
                    request: android.webkit.WebResourceRequest
                ): Boolean {
                    val uri = request.url
                    val origin = prefs.getString("url", "") ?: ""
                    val host = Uri.parse(origin).host
                    if (uri.host == "accounts.google.com" ||
                        uri.host == "oauth2.googleapis.com" ||
                        (uri.host != null && uri.host != host)) {
                        startActivity(Intent(Intent.ACTION_VIEW, uri))
                        return true
                    }
                    return false
                }
            }
        }
        root.addView(heading)
        root.addView(address)
        root.addView(connect)
        root.addView(help)
        root.addView(web, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        // Do not automatically launch the browser when settings are opened.
    }

    private fun openCompanion() {
        val url = address.text.toString().trim().trimEnd('/')
        val uri = Uri.parse(url)
        if (uri.scheme != "https" || uri.host.isNullOrBlank() || uri.userInfo != null) {
            address.error = "Use a valid HTTPS server URL"
            return
        }
        prefs.edit().putString("url", url).apply()
        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }

    @Deprecated("Deprecated in Android SDK")
    override fun onBackPressed() {
        if (web.canGoBack()) web.goBack() else super.onBackPressed()
    }

    override fun onDestroy() {
        web.destroy()
        super.onDestroy()
    }
}
