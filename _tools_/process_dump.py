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

import base64
from collections import defaultdict
import click
import re
import tqdm
import json
from pathlib import Path
from urllib.parse import urlsplit, unquote


def get_sif_files(fields):
    return [
        f for f in fields['files']
        if (f.get('name', '').endswith('.sif')
            or f.get('name', '').endswith('.simg')
            or f.get('name', '').endswith('.img.gz')
            )
    ]


def get_path_from_url(url):
    """Given image url, extract path to image within monolith"""
    u = urlsplit(url)
    if not u.netloc in ('storage.googleapis.com', 'www.googleapis.com'):
        import pdb; pdb.set_trace()
    pref = '%2Fgithub.com%2F'
    if not u.path.index(pref):
        import pdb; pdb.set_trace()
    p = unquote(u.path[u.path.index(pref) + len(pref):])
    # legacy were tuned up to include the same md5 dir/ for consistency:
    if '/singularityhub-legacy/' in url:
        pp = Path(p)
        md5 = pp.name[:32]
        p = str(pp.parent / md5 / pp.name)
    return p


def from_annex_key(key):
    res = re.match("(?P<backend>MD5E)-s(?P<size>\d+)--(?P<md5>[0-9a-f]{32})(?P<ext>.*)", key)
    assert res
    return res.groupdict()


@click.command()
@click.argument("dump_path", type=click.Path(exists=True, file_okay=False))
@click.argument("monolith_path", type=click.Path(exists=True, file_okay=False))
@click.argument("output_json", type=click.Path(exists=False, file_okay=True))
# TODO: option to point to filestore so we could check
def main(dump_path, monolith_path, output_json):
    recs = defaultdict(list)
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
                "branch": fields["branch"],
                "tag": fields["tag"],
                "commit": fields["commit"],
                "version": fields["version"],
                "build_date": fields["build_date"],
                # this is apparently not a size of the image!
                # API does report it as well. correct 'size': '62652447',
                # is in 'files' record
                "size_mb": fields['metrics'].get('size_mb'),
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
            target_file = None
            if target_file:
                assert len(sif_files) == 1
                assert sif_files[0] == target_file
            elif sif_files:
                assert len(sif_files) == 1
                # Happens for all the "http://datasets.datalad.org/"
                # redirects already + a few in https://storage.googleapis.com/
                # Let's fish out among files
                target_file = sif_files[0]

            # Parse monolith's annex key for extra check for paranoids
            # + to handle the cases where we do not have proper record
            # but do have a url
            img_url = fields['image']
            if 'datasets.datalad.org' in img_url:
                assert target_file
                img_url = target_file['mediaLink']
            mon_relpath = get_path_from_url(img_url)
            mon_path = (Path(monolith_path) / mon_relpath)
            if not mon_path.is_symlink():
                raise RuntimeError(f"Found no symlink under {mon_path}")
            annex_key_parsed = from_annex_key(mon_path.readlink().name)

            if target_file:
                target_file['md5'] = base64.b16encode(
                    base64.b64decode(target_file['md5Hash'])).lower().decode()
                assert target_file['md5'] == annex_key_parsed['md5']
                assert target_file['size'] == annex_key_parsed['size']
                # strip away leading prefix including github.com
                pref = '/github.com/'
                # just use the one we deduced in monolith -- will be fixed
                # for singularityhub-legacy
                target_file['name'] = mon_relpath  # target_file['name'][target_file['name'].index(pref) + len(pref):]
            else:
                # it still might be there and may be just a bug in DB?
                # TODO: check e.g. for BarquistLab/proQ_conventionalMouse_dataAnalysis
                # tag def
                #print(f"Found no target image file for {fields['name']}:{fields['tag']} . "
                #      f"Image url was {fields['image']} but found no matching file record")
                # So we will deduce it from the image URL
                target_file = {
                    'name': mon_relpath,
                    'size': int(annex_key_parsed['size']),
                    'md5': annex_key_parsed['md5']
                }
            # TODO: just store relevant   image?
            rec['file'] = target_file['name']
            assert rec['file'].count('/') == 4
            rec['size'] = int(target_file['size'])
            rec['md5'] = target_file['md5']
            recs[fields['name']].append(rec)

    # TODO: traverse monolith and ensure that we do no have some images which
    # are not in our output record
    all_under_monolith = (str(p.relative_to(monolith_path)) for p in Path(monolith_path).glob('*/*'))
    all_under_monolith = set(x for x in all_under_monolith if not (x.startswith('.') or x.startswith('_')))

    # should be given since we did test all the images above
    assert not set(recs).difference(all_under_monolith)
    # but here we discover a good number of prefixes which do not have DB dump record
    loose_collections = all_under_monolith.difference(recs)
    if loose_collections:
        print(
            f"WARNING: found {len(loose_collections)}  out of {len(all_under_monolith)} loose collections "
            f"(having no image in main.container.json): {loose_collections}")
    with open(output_json, 'w') as f:
        json.dump(recs, f, indent=2)  # TODO: remove indent for production


if __name__ == '__main__':
    main()



"""
Need following for the results to return
  "id": 11888,                                                                                                                                                                                                       
  "name": "ReproNim/reproin",                                                                                                                                                                                        
  "branch": "master",                                                                                                                                                                                                
  "commit": "7def9299ea40bd191efb5b3ab5f3bdc3c2c4b62d",                                                                                                                                                              
  "tag": "latest",                                                                                                                                                                                                   
  "version": "361dd7824960bb8eb43b699f90b977cf",                                                                                                                                                                     
  "size_mb": 1332,                                                                                                                                                                                                   
  "image":  

sample rec
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