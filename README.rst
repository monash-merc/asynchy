ASSyncy
=======

ASSyncy is the tool responsible for downloading MX data from the Austrlaian
Synchrotron SFTP server to M3. It consistes of two python programs (to be installed via
pip into a virutalenv)

mxsync is a service (daemon) that runs on m3-dtn1. It periodically look for new 
data sets to download from AS and runs an rsync. It only does this for data sets
for which it can work out the correct M3 group to set ownership to. It keeps and
in memory list of datasets downloaded.

epngroups is a script run via cronjob that looks for data that we have access to
and emails about any data we have access to that we don't know the owerership for.
This is actually useless ATM because we have access to all Monash AS data regardless
of wheterh the owner is on M3 or not. We need to revoke this access but the MyTardis
team currently relies on it as part of data repatriation.

Installation is via pip on m3-dtn1 in /opt/mx_sync.
This particular install was done with "-e" which means you cna
cd /opt/mx_sync/src/ASsyncy and git pull if you need to deploy updates

config file sare in /opt/mx_sync/etc on m3-dtn1. 
