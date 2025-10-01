import os
import requests
import zipfile
import geopandas as gpd
from tqdm import tqdm

# URL template
URL_TEMPLATE = "https://www.wien.gv.at/ma41datenviewer/downloads/geodaten/fmzk_gp/{x}_{y}_fmzk_gp.zip"

# Output paths
DOWNLOAD_DIR = "datasets/fmzk-parts"
MERGED_GPKG = "datasets/fmzk.gpkg"

# Ensure download dir exists (don't recreate, just use existing)
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

gpkg_files = []

print("Starting downloads...")

# Loop through possible x,y combinations
for x in range(12, 60):
    for y in range(1, 5):
        expected_gpkg = os.path.join(DOWNLOAD_DIR, f"{x}_{y}_FMZK_GP.gpkg")
        if os.path.exists(expected_gpkg):
            print(f"Skipping download for {x}_{y}, file already exists.")
            gpkg_files.append(expected_gpkg)
            continue

        url = URL_TEMPLATE.format(x=x, y=y)
        zip_path = os.path.join(DOWNLOAD_DIR, f"{x}_{y}.zip")

        try:
            response = requests.get(url, stream=True, timeout=60)
            if response.status_code == 200:
                with open(zip_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"Downloaded {url}")

                # Extract gpkg
                try:
                    with zipfile.ZipFile(zip_path, "r") as z:
                        z.extractall(DOWNLOAD_DIR)
                        for fname in z.namelist():
                            if fname.endswith(".gpkg"):
                                gpkg_path = os.path.join(DOWNLOAD_DIR, fname)
                                gpkg_files.append(gpkg_path)
                except zipfile.BadZipFile:
                    print(f"Corrupted or invalid zip at {url}")

                os.remove(zip_path)
            else:
                print(f"No file at {url} (status {response.status_code})")
        except Exception as e:
            print(f"Failed to download {url}: {e}")

print("\nMerging GeoPackages...")

# Merge all GPKGs
if gpkg_files:
    merged_gdf = []
    for gpkg in tqdm(gpkg_files, desc="Merging"):
        try:
            gdf = gpd.read_file(gpkg)
            merged_gdf.append(gdf)
        except Exception as e:
            print(f"Skipping {gpkg} due to read error: {e}")

    if merged_gdf:
        final = gpd.GeoDataFrame(
            gpd.pd.concat(merged_gdf, ignore_index=True), crs=merged_gdf[0].crs
        )
        final.to_file(MERGED_GPKG, driver="GPKG", layer="fmzk", mode="w")
        print(f"Saved merged GeoPackage as {MERGED_GPKG}")
    else:
        print("All files failed to load, nothing to merge.")
else:
    print("No GeoPackages were downloaded, nothing to merge.")
