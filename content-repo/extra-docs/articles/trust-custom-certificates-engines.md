---
id: trust-custom-certificates-engines
title: Configure Engines to Trust Custom Certificates
description: Replace the self-signed certificate for an engine with a valid CA certificate.
---
To secure the connection between the server and the engine, you can replace the self-signed certificate for an engine with a valid CA certificate.

1. Find the two files created by the engine. The default location is /usr/local/demisto.  
d1.key.pem  
d1.cert.pem   
3. Replace the contents of these files with your own certificates.
4. Change file owner to demisto.  
chown -R demisto:demisto d1.key.pem  
chown -R demisto:demisto d1.cert.pem
4. Set the file permissions.  
chmod 600 d1.key.pem  
chmod 644 d1.cert.pem