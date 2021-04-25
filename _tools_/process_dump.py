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
import itertools
import os.path as op
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

@click.group()
def main():
    pass


@main.command()
@click.argument("dump_path", type=click.Path(exists=True, file_okay=False))
@click.argument("monolith_path", type=click.Path(exists=True, file_okay=False))
@click.argument("output_json", type=click.Path(exists=False, file_okay=True))
# TODO: option to point to filestore so we could check
def dump_data(dump_path, monolith_path, output_json):
    recs = defaultdict(list)
    monolith_path = Path(monolith_path)
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
            mon_path = (monolith_path / mon_relpath)
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
            rec['collection'] = fields['collection']
            assert rec['file'].count('/') == 4
            rec['size'] = int(target_file['size'])
            rec['md5'] = target_file['md5']
            recs[fields['name']].append(rec)

    # TODO: traverse monolith and ensure that we do no have some images which
    # are not in our output record
    # Part1 : report (no act) on entire collections
    # Part2 : filtering and reshaping paths I think I will do in a separate command
    all_under_monolith = (str(p.relative_to(monolith_path)) for p in monolith_path.glob('*/*'))
    all_under_monolith = set(x for x in all_under_monolith if not (x.startswith('.') or x.startswith('_')))

    # should be given since we did test all the images above
    assert not set(recs).difference(all_under_monolith)
    # but here we discover a good number of prefixes which do not have DB dump record
    loose_collections = all_under_monolith.difference(recs)
    if loose_collections:
        print(
            f"WARNING: found {len(loose_collections)}  out of {len(all_under_monolith)} loose collections "
            f"(having no image in main.container.json): {loose_collections}")

    collections = {}
    missing_dir = {}
    with (Path(dump_path) / "main.collection.json").open() as f:
        orig_recs = json.load(f)
        for r in orig_recs:
            repo = ((r.get('fields') or {}).get("repo") or {})
            full_name = repo.get('full_name')
            rec = {
                'license': repo.get('license'),
                'full_name': full_name,
            }
            # Don't do check here -- some collections might not correspond since
            # might have been renamed etc. So we will just store all
            # if not (monolith_path / full_name).is_dir():
            #     # print(f"WARNING: no monolith dir for {r['pk']}: {full_name}")
            #     missing_dir[int(r['pk'])] = rec
            # else:
            collections[int(r['pk'])] = rec
    print(f"INFO: collected {len(collections)} collections")
    if missing_dir:
        print(
            f"WARNING: following {len(missing_dir)} collections had nothing in monolith, and thus skipped:"
            f" {(', '.join(map(str, missing_dir)))}"
        )

    for collection, containers in recs.items():
        for container in containers:
            container.update(get_shorter_file_rec(container))

    data = {
        "images": recs,
        "collections": collections,
    }
    with open(output_json, 'w') as f:
        json.dump(data, f, indent=2)


def get_shorter_file_rec(r):
    r_ = r.copy()
    if 'file_orig' in r:
        # rerunning?
        f = r.get('file_orig')
    else:
        f = r.get('file')
    assert f
    r_['file_orig'] = f
    p = Path(f)
    pp = p.parts
    assert len(pp) == 5  # we must be consistent now
    new_pp = [
        pp[0], pp[1],
        r_['tag'],
        # shorter and hopefully a bit more useful than full hex strings 2nd level directory
        f"{r_['build_date'][:10]}-{r_['commit'][:8]}-{pp[3][:8]}",
        pp[-1]  # filename original
    ]
    r_['file'] = op.join(*new_pp)
    return r_


@main.command()
@click.argument("monolith_path", type=click.Path(exists=True, file_okay=False))
@click.argument("images_json", type=click.Path(exists=True, file_okay=True))
# TODO: option to point to filestore so we could check
def rename_remove(monolith_path, images_json):
    """Take new "file" paths and rename, and also remove those which are not known"""
    from datalad.support.annexrepo import AnnexRepo
    repo = AnnexRepo(monolith_path)
    with open(images_json) as f:
        data = json.load(f)

    # Tired yoh cannot get it why we ending up with string keys in json - not supported?
    for pk in list(data['collections']):
        data['collections'][int(pk)] = data['collections'].pop(pk)

    # Remove all collections which are not included
    known_collections = {r['full_name']: int(pk) for pk, r in data['collections'].items()}
    # Add those which might have been renamed but still present under original names
    # in the actual container images file tree
    for col, containers in data['images'].items():
        for r in containers:
            col_ = op.join(*Path(r['file_orig']).parts[:2])
            if col_ in known_collections:
                # in case of narrative/remoll  there is 214 with image
                # and 254 without image :-/ So we cannot assert
                # assert known_collections[col_] == int(r['collection'])
                # Let's just inform - and it seems we have just few
                if known_collections[col_] != int(r['collection']):
                    print(f"WARNING: for {col_} known as {known_collections[col_]} we also have {r['collection']}")
            else:
                known_collections[col_] = r['collection']
                # and we need to adjust mapping since that is where it would be found now
                rcol = data['collections'][r['collection']]
                if 'full_name_orig' not in rcol:
                    rcol['full_name_orig'] = rcol['full_name']
                rcol['full_name'] = col_

    dirs_under_monolith = set(str(p.relative_to(monolith_path)) for p in Path(monolith_path).glob('*/*/*/*'))
    dirs_under_monolith = set(x for x in dirs_under_monolith if not (x.startswith('.') or x.startswith('_')))
    # group by collection
    cols_under_monolith = defaultdict(list)
    for d in dirs_under_monolith:
        cols_under_monolith[op.join(*Path(d).parts[:2])].append(d)

    dirs_images = list(itertools.chain(
        *([op.dirname(x['file']) for x in recs] for recs in data['images'].values())
    ))
    # import pdb; pdb.set_trace()

    for c, dirs in cols_under_monolith.items():
        continue
        if c not in known_collections:
            print(f"Removing {c}")
            ## repo.call_git(['rm', '-rf', c])
        else:
            print(f"Renaming for {c}")
            # for container

    # we might have adjusted collections
    with open(images_json, 'w') as f:
        json.dump(data, f, indent=2)


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