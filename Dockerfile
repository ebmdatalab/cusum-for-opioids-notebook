FROM ebmdatalab/datalab-jupyter:python3.8.1-0ba7fd7eb2604eaebd39875f60988de3470ca727

# Although the usual development workflow mounts the local folder (so
# that edits appear in the host filesystem, for git versioning), we also
# COPY *everything* into the home directory so that this Dockerfile can
# also run in mybinder
COPY . /home/app/notebook

# Hack until this is fixed https://github.com/jazzband/pip-tools/issues/823
USER root
RUN chmod 644 /home/app/notebook/requirements.txt
USER app
RUN pip install --requirement /home/app/notebook/requirements.txt

# This is a custom ipython kernel that allows us to manipulate
# `sys.path` in a consistent way between normal and pytest-with-nbval
# invocations
RUN jupyter kernelspec install /home/app/notebook/config/ --user --name="python3"

EXPOSE 8888

# We use a custom entrypoint so that we can be invoked by mybinder
# with custom arguments
ENTRYPOINT ["/home/app/notebook/docker_entrypoint.sh", "/home/app/notebook"]
