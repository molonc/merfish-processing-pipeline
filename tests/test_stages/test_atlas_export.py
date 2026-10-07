
"""
        Tests For Altas Export Stage
"""

import pytest

from merfish_pipeline.stages.atlas_export import merge_fov
from tempfile import NamedTemporaryFile
import os
import numpy as np
import pandas as pd
import tifffile 

class TestMergeFOV:
    def __build_manifest(self, nfovs:int = 2, shape:tuple[int] = (8,2,3,256,256)) -> pd.DataFrame:
        assert len(shape) == 5, "Only 5D stacks are supported"
        rows = {}
        i = 0
        for fov in range(nfovs):
            for t in range(shape[0]):
                for c in range(shape[1]):
                    for z in range(shape[2]):
                        f = NamedTemporaryFile(suffix=".tiff", delete=False, delete_on_close=True)
                        plane = np.random.randint(0, 2**16 - 1, size=shape[3:], dtype=np.uint16)
                        tifffile.imwrite(f.name, plane)
                        
                        # Hash the bytes, not the array directly
                        rows[i] = (fov, t + 1, c, z + 1, f.name, hash(plane.tobytes()), f)
                        i += 1
                        
        return pd.DataFrame.from_dict(
            rows, 
            orient='index', 
            columns=["fov", "round", "channel", "z_slice", "abs_path", "plane_hash", "file_handle"]
        )

    def __teardown(self, manifest:pd.DataFrame, hyperstacks:list) -> None:
        for f in manifest['file_handle']:
            f.close()
        for hyperstack in hyperstacks:
            hyperstack.close()

    def __assert_equal(self, manifest:pd.DataFrame, fov:int, hyperstack:str) -> bool:
        fov_meta = manifest.loc[manifest['fov'] == fov, :]
        
        # Use tifffile to read the TIFF stack created by merge_fov
        stack = tifffile.imread(hyperstack)
        
        for row in fov_meta.itertuples(index=False):
            stack_plane = stack[row.round - 1, row.channel, row.z_slice - 1, :, :]
            
            # Use proper assert comma syntax and byte hashing
            assert hash(stack_plane.tobytes()) == row.plane_hash, "Hashing Original Image and Sliced Hyperstack are not equal --> Stack Incorrectly inserted"
            
        return True
        
    def test_merge_single_fov(self, shape=(2,2,2,128,128)):
        manifest = self.__build_manifest(nfovs=1, shape=shape)
        hyperstack = NamedTemporaryFile(suffix=".tiff", delete=False, delete_on_close=True)
        ome = {
            "axes": "TCZYX",
            "PhysicalSizeX": 0.1,
            "PhysicalSizeY": 0.1,
            "PhysicalSizeZ": 0.1,
            "PhysicalSizeUnitX": "um",
            "PhysicalSizeUnitY": "um",
            "PhysicalSizeUnitZ": "um",
        }
        
        # Fixed index to shape[1] for channels
        channel_lut = pd.Series(index=np.arange(shape[1]), data=np.arange(shape[1]))
        
        merge_fov(
            0,
            (hyperstack.name, ome),
            manifest,
            shape,
            "uint16",
            channel_lut
        )
        
        self.__assert_equal(manifest, 0, hyperstack.name)
        self.__teardown(manifest, [hyperstack])
    
    def test_merge_multi_fov(self, shape=(2,2,2,128,128)):
            # Generate a manifest with multiple FOVs
            nfovs = 3
            manifest = self.__build_manifest(nfovs=nfovs, shape=shape)
            
            ome = {
                "axes": "TCZYX",
                "PhysicalSizeX": 0.1,
                "PhysicalSizeY": 0.1,
                "PhysicalSizeZ": 0.1,
                "PhysicalSizeUnitX": "um",
                "PhysicalSizeUnitY": "um",
                "PhysicalSizeUnitZ": "um",
            }
            
            channel_lut = pd.Series(index=np.arange(shape[1]), data=np.arange(shape[1]))
            
            # Keep track of generated hyperstack files for teardown
            hyperstacks = []
            
            # Iterate over each FOV, merge, and assert equality
            for fov in range(nfovs):
                hyperstack = NamedTemporaryFile(suffix=".tiff", delete=False, delete_on_close=True)
                hyperstacks.append(hyperstack)
                
                merge_fov(
                    fov,
                    (hyperstack.name, ome),
                    manifest,
                    shape,
                    "uint16",
                    channel_lut
                )
                
                self.__assert_equal(manifest, fov, hyperstack.name)
                
            # Clean up the manifest temporary files and all generated hyperstacks
            self.__teardown(manifest, hyperstacks)
    def test_validate_ome_metadata(self, shape=(1, 1, 1, 64, 64)):
            manifest = self.__build_manifest(nfovs=1, shape=shape)
            hyperstack = NamedTemporaryFile(suffix=".tiff", delete=False, delete_on_close=True)
            
            # FIX: Changed PhysicalSizeUnitX to PhysicalSizeXUnit, etc.
            ome = {
                "axes": "TCZYX",
                "PhysicalSizeX": 0.123,
                "PhysicalSizeY": 0.456,
                "PhysicalSizeZ": 0.789,
                "PhysicalSizeXUnit": "µm",
                "PhysicalSizeYUnit": "µm",
                "PhysicalSizeZUnit": "µm",
            }
            
            channel_lut = pd.Series(index=np.arange(shape[1]), data=np.arange(shape[1]))
            
            merge_fov(
                0,
                (hyperstack.name, ome),
                manifest,
                shape,
                "uint16",
                channel_lut
            )
            
            # Read the file and validate the OME-XML metadata
            with tifffile.TiffFile(hyperstack.name) as tif:
                assert tif.is_ome, "Output TIFF is not marked as an OME-TIFF."
                
                ome_xml = tif.ome_metadata
                assert ome_xml is not None, "OME metadata is missing from the TIFF file."
                
                assert 'PhysicalSizeX="0.123"' in ome_xml, "PhysicalSizeX incorrectly written."
                assert 'PhysicalSizeY="0.456"' in ome_xml, "PhysicalSizeY incorrectly written."
                assert 'PhysicalSizeZ="0.789"' in ome_xml, "PhysicalSizeZ incorrectly written."
                
                # FIX: Check for PhysicalSizeXUnit instead of PhysicalSizeUnitX
                assert 'PhysicalSizeXUnit="µm"' in ome_xml or 'PhysicalSizeXUnit="um"' in ome_xml, "PhysicalSizeXUnit incorrectly written."
                assert 'PhysicalSizeYUnit="µm"' in ome_xml or 'PhysicalSizeYUnit="um"' in ome_xml, "PhysicalSizeYUnit incorrectly written."
                assert 'PhysicalSizeZUnit="µm"' in ome_xml or 'PhysicalSizeZUnit="um"' in ome_xml, "PhysicalSizeZUnit incorrectly written."
                
            self.__teardown(manifest, [hyperstack])

                    
                                 




