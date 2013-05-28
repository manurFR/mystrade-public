Before making the first "git push", the following two files should be copied (scp) to the production server:
1. "post-receive" should be copied on the server, under the "hooks" directory in the git repository,
   and given executable rights if needed (chmod +x post-receive).
2. "deploy.sh" should be copied on the server, under the "production" directory in the future working tree
   ($HOME/mystrade/production), and given executable rights if needed.

The other deployment steps should be taken care of automatically at the end of each "git push" once this is done.