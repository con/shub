# (Read-only) Singularity-hub.org (shub://) Archive

This is a DataLad dataset containing all singularity images built and provided by singularity-hub.org as of April 19, 2021.
The main purpose of this dataset is to provide contingency and assist with reproducibility of the prior studies which used and referenced datasets on singularity-hub.org.
["Singularity Hub is going read-only" announcement](https://singularityhub.github.io/singularityhub-docs/2021/going-read-only/) gives more information about the transition, and available alternative ways to build new versions of the containers.

## Motivation

The motivation for establishing this dataset and service is under auspice of [ReproNim](http://repronim.org): to keep scientific research reproducible!
The original https://singularity-hub.org provided great service to the scientific community across wide-range of disciplines.
Many research projects and papers used singularity containers built and provided by the singularity-hub.org.
We considered that it would have been a big loss if those containers simply disappeared.

## HOWTO use it

### `singularity pull shub://`

The effort was made to serve all already existing containers as it was done before, so your scripts and documentations should remain valid.

### DataLad (or just git + git-annex)

You can `datalad install ///shub` to obtain entire collection on your harddrive with subsequent `datalad get` for the specific containers of interest.  Then `singularity run` or `singularity exec` could be used normally by pointing to the specific container.
If you are to go DataLad route, we would advise you to install this dataset as a subdataset within your specific study/analysis dataset, so you do not only have a "copy" of it, but also have a provenance record on where you have obtained it from.
Such setup follows ["YODA principles"](https://github.com/myyoda/myyoda) we encourage you to familiarize yourself with.  

### DataLad-container

TODO: Populate datalad-container configuration (see [https://github.com/con/shub/issues/1](https://github.com/con/shub/issues/1))

## Support

As this is just intended to provide a historical archive, no further development is envisioned.  But if you run into an issue, such as some container is no longer available whenever you are `>99%` certain it was available as of April 19, 2021 - please file an issue on https://github.com/con/shub/issues .

## For developers

- [`_service_/`](_service_/) directory in this dataset contains code and container for a lightweight sanic webserver to serve shub:// urls to `singularity` client.
  - [`_data_/images.json`](_data_/images.json) - the harmonized metadata used by the sanic webserver
- [`_tools_/`](_tools_/) - original scripts used to prepare this dataset and `images.json`

# Acknowledgements

We are very grateful to the original author and maintainer of the singularity-hub.org (https://github.com/vsoch) not only for all her work and service with https://singularity-hub.org, but also for letting us to archive all the containers and thus to give them the "after-life".

Hosting is provided by http://centerforopenneuroscience.org at [Psychological and Brain Sciences Department](https://pbs.dartmouth.edu) of [Dartmouth College](https://dartmouth.edu/), which also provides the network bandwidth for this endeavor.
