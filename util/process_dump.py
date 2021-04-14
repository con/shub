#!/usr/bin/env python3
# emacs: -*- mode: python-mode; py-indent-offset: 4; tab-width: 4; indent-tabs-mode: nil -*-
# ex: set sts=4 ts=4 sw=4 noet:
"""

 COPYRIGHT: Yaroslav Halchenko 2021

 LICENSE: MIT

  Permission is hereby granted, free of charge, to any person obtaining a copy
  of this software and associated documentation files (the "Software"), to deal
  in the Software without restriction, including without limitation the rights
  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
  copies of the Software, and to permit persons to whom the Software is
  furnished to do so, subject to the following conditions:

  The above copyright notice and this permission notice shall be included in
  all copies or substantial portions of the Software.

  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
  THE SOFTWARE.
"""

__author__ = 'yoh'
__license__ = 'MIT'

import click
import tqdm
import json
from pathlib import Path


def get_sif_files(fields):
    return [
        f for f in fields['files']
        if (f.get('name', '').endswith('.sif')
            or f.get('name', '').endswith('.simg')
            or f.get('name', '').endswith('.img.gz')
            )
    ]

@click.command()
@click.argument("dump_path", type=click.Path(exists=True, file_okay=False))
@click.argument("output_json", type=click.Path(exists=False, file_okay=True))
# TODO: option to point to filestore so we could check
def main(dump_path, output_json):
    recs = []
    with (Path(dump_path) / "main.container.json").open() as f:
        orig_recs = json.load(f)
        for dbrec in tqdm.tqdm(orig_recs):
            fields = dbrec['fields']
            # if 'hello' in fields['image']:
            #     import pdb; pdb.set_trace()
            if not fields['image']:
                # just for paranoids
                assert not get_sif_files(fields)
                # has no image - skip
                continue
            rec = {
                "id": dbrec["pk"],
                "name": fields["name"],
                "branch": fields["branch"],
                "tag": fields["tag"],
                "commit": fields["commit"],
                "version": fields["version"],
                # this is apparently not a size of the image!
                # API does report it as well. correct 'size': '62652447',
                # is in 'files' record
                "size_mb": fields['metrics'].get('size_mb'), # some other size ;)
            }
            # it seems we can match based on image and mediaLink
            target_file = None
            for f in fields['files']:
                if f['mediaLink'] == fields['image']:
                    target_file = f
                    break
            sif_files = get_sif_files(fields)
            # if len(sif_files) != 1:
            #     import pdb; pdb.set_trace()
            # assert len(sif_files) == 1
            if target_file:
                assert len(sif_files) == 1
                assert sif_files[0] == target_file
            elif sif_files:
                assert len(sif_files) == 1
                # Happens for all the "http://datasets.datalad.org/"
                # redirects already + a few in https://storage.googleapis.com/
                # Let's fish out among files
                target_file = sif_files[0]
            else:
                # it still might be there and may be just a bug in DB?
                # TODO: check e.g. for BarquistLab/proQ_conventionalMouse_dataAnalysis
                # tag def
                print(f"Found no target image file for {fields['name']}:{fields['tag']} . "
                      f"Image url was {fields['image']} but found no matching file record")
                continue
            # TODO: just store relevant   image?
            rec['file'] = target_file
            recs.append(rec)
    """Need following for the results to return
  "id": 11888,                                                                                                                                                                                                       
  "name": "ReproNim/reproin",                                                                                                                                                                                        
  "branch": "master",                                                                                                                                                                                                
  "commit": "7def9299ea40bd191efb5b3ab5f3bdc3c2c4b62d",                                                                                                                                                              
  "tag": "latest",                                                                                                                                                                                                   
  "version": "361dd7824960bb8eb43b699f90b977cf",                                                                                                                                                                     
  "size_mb": 1332,                                                                                                                                                                                                   
  "image":  
  """
    with open(output_json, 'w') as f:
        json.dump(recs, f, indent=2)  # TODO: remove indent for production


if __name__ == '__main__':
    main()



"""
    'collection': 17,
    'branch': 'master',
    'tag': 'latest',
    'name': 'vsoch/hello-world',
    'build_date': '2021-04-12T12:26:14.487Z',
    'build_log': 'True',
    'files': [
        {
            'id': 'singularityhub/singularityhub/github.com/vsoch/hello-world/3bac21df631874e3cbb3f0cf6fc9af1898f4cc3d/104932c9ca80c0eb90ebf6a80b7d7400/104932c9ca80c0eb90ebf6a80b7d7400.sif/1563547843599870',
            'etag': 'CP67us6dweMCEAE=',
            'kind': 'storage#object',
            'name': 'singularityhub/github.com/vsoch/hello-world/3bac21df631874e3cbb3f0cf6fc9af1898f4cc3d/104932c9ca80c0eb90ebf6a80b7d7400/104932c9ca80c0eb90ebf6a80b7d7400.sif',
            'size': '62652447',
            'bucket': 'singularityhub',
            'crc32c': '8VqIHA==',
            'md5Hash': 'EEkyycqAwOuQ6/aoC310AA==',
            'updated': '2019-07-19T14:50:43.599Z',
            'selfLink': 'https://www.googleapis.com/storage/v1/b/singularityhub/o/singularityhub%2Fgithub.com%2Fvsoch%2Fhello-world%2F3bac21df631874e3cbb3f0cf6fc9af1898f4cc3d%2F104932c9ca80c0eb90ebf6a80b7d7400%2F1
04932c9ca80c0eb90ebf6a80b7d7400.sif',
            'mediaLink': 'https://www.googleapis.com/download/storage/v1/b/singularityhub/o/singularityhub%2Fgithub.com%2Fvsoch%2Fhello-world%2F3bac21df631874e3cbb3f0cf6fc9af1898f4cc3d%2F104932c9ca80c0eb90ebf6a80b
7d7400%2F104932c9ca80c0eb90ebf6a80b7d7400.sif?generation=1563547843599870&alt=media',
            'generation': '1563547843599870',
            'contentType': 'text/plain',
            'timeCreated': '2019-07-19T14:50:43.599Z',
            'storageClass': 'REGIONAL',
            'metageneration': '1',
            'timeStorageClassUpdated': '2019-07-19T14:50:43.599Z'
"""