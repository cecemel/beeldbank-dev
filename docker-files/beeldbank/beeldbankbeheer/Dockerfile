FROM python:2.7

RUN apt-get update
RUN apt-get install -y libgeos-c1 libgeos-3.4.2
RUN apt-get install -y imagemagick
RUN pip install sphinx
RUN apt-get install -y ghostscript
COPY requirements.txt /app/
COPY requirements-dev.txt /app/

WORKDIR "/app"
ARG GITUSER="USERNAME_NEEDED"
ARG GITPW="PASSWORD_NEEDED"
# TODO: fix this in a proper settings file
RUN pip install -e git+https://$GITUSER:$GITPW@github.com/OnroerendErfgoed/oeauth.git@1.0.0#egg=oeauth
RUN pip install -e git+https://$GITUSER:$GITPW@github.com/OnroerendErfgoed/pyramid_oeauth.git@1.1.1#egg=pyramid_oeauth
RUN pip install -e git+https://github.com/OnroerendErfgoed/pyoes.git@0.4.7#egg=pyoes
RUN pip install -e git+https://github.com/OnroerendErfgoed/oe_utils.git@0.14.0#egg=oe_utils
RUN pip install -e git+https://github.com/OnroerendErfgoed/crabpy_pyramid.git@0.6.2#egg=crabpy_pyramid
RUN pip install -e git+https://github.com/OnroerendErfgoed/crabpy.git@0.8.0#egg=crabpy
RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt
COPY . /app

RUN python setup.py develop
CMD pserve development.ini
