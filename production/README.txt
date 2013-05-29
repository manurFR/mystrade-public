Before making the first "git push", the following tree should be prepared on the production server's home directory:

$HOME
|-- admin
|   ...
|-- cgi-bin
|   ...
|-- git
|   `-- mystrade.git [1]
|       |-- HEAD
|       |-- ORIG_HEAD
|       |-- branches
|       |   ...
|       |-- config
|       |-- description
|       |-- hooks
|       |   `-- post-receive [+x] [2]
|       |-- index
|       |-- info
|       |   ...
|       |-- objects
|       |   ...
|       |-- packed-refs
|       `-- refs
|           ...
|-- mystrade
|   |-- production
|   |   `-- deploy.sh [+x] [2]
|   `-- public
|       |-- django.fcgi [+x] [2]
|       |-- media -> /usr/local/alwaysdata/python/django/1.5.1/django/contrib/admin/media/
|       `-- static
|           ...
`-- python-modules
    ...

[1] bare git repository cloned ("git clone --bare mystrade/ mystrade.git") and scp'ed from the mystrade git repository
[2] these three files should be copied (scp) from the "production" folder to the corresponding folder on the server
[+x] these files should be executable on the server ("chmod +x <file>" if they are not)

The deployment should then be performed automatically at the end of each "git push".