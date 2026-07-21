import hudson.security.FullControlOnceLoggedInAuthorizationStrategy
import hudson.security.HudsonPrivateSecurityRealm
import hudson.security.csrf.DefaultCrumbIssuer
import jenkins.model.Jenkins
import jenkins.model.JenkinsLocationConfiguration
import hudson.model.User

def jenkins = Jenkins.get()
def location = JenkinsLocationConfiguration.get()
def configuredUrl = System.getenv('JENKINS_URL') ?: 'http://127.0.0.1:8080/'

// Do not overwrite a URL configured through the Jenkins UI.
if (!location.getUrl()?.trim()) {
    location.setUrl(configuredUrl)
    location.save()
}

// Security is opt-in through an external secret; never commit a password.
def password = System.getenv('JENKINS_ADMIN_PASSWORD')
if (password?.trim() && !jenkins.isUseSecurity()) {
    def userId = System.getenv('JENKINS_ADMIN_ID') ?: 'admin'
    def realm = new HudsonPrivateSecurityRealm(false)
    if (!User.getById(userId, false)) {
        realm.createAccount(userId, password)
    }
    jenkins.setSecurityRealm(realm)

    def authorization = new FullControlOnceLoggedInAuthorizationStrategy()
    authorization.setAllowAnonymousRead(false)
    jenkins.setAuthorizationStrategy(authorization)
    jenkins.setCrumbIssuer(new DefaultCrumbIssuer(true))
    jenkins.save()
}
