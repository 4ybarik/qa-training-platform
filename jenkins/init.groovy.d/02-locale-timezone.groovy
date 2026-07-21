// Keep the controller locale deterministic instead of inheriting the browser
// Accept-Language header. Jenkins core and plugins that ship Russian catalogs
// will use Russian; plugins without a Russian catalog may still show English
// labels, which is a translation limitation rather than a runtime error.
import hudson.plugins.locale.PluginImpl

def localeConfig = PluginImpl.get()
localeConfig.setSystemLocale('ru')
localeConfig.setIgnoreAcceptLanguage(true)
localeConfig.setAllowUserPreferences(false)
localeConfig.save()

println('Jenkins locale configured: ru (browser and per-user overrides disabled)')
