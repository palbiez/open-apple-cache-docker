// PAC helper: copy into an existing PAC; see APPLE-PROXY.md for integration.
function isAppleServiceHost(host) {
    host = host.toLowerCase().replace(/\.$/, "");
    var domains = ["apple.com", "itunes.com", "mzstatic.com", "cdn-apple.com",
        "icloud.com", "icloud-content.com", "apple-cloudkit.com"];
    for (var i = 0; i < domains.length; i++) {
        if (host === domains[i] || dnsDomainIs(host, "." + domains[i])) return true;
    }
    // Only this Apple hostname on the shared CDN, not the whole CDN domain.
    return host === "appldnld.apple.com.edgesuite.net";
}
