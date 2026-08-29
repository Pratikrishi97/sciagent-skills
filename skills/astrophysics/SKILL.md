---
name: astrophysics
description: Astrophysics workflows using astropy for units, coordinates (SkyCoord), time (Time), cosmology, and FITS I/O with astropy.io.fits and WCS, photutils for aperture and PSF photometry, specutils for 1-D spectroscopy, poliastro for celestial mechanics, yt for AMR-based galaxy and cosmology visualization, and astroquery for SIMBAD, VizieR, and TAP catalog cross-matches. Use when handling FITS images or spectra, building sky coordinates, cross-matching catalogs, performing photometry, or simulating orbits.
license: MIT
compatibility: Requires Python 3.10+ with astropy, photutils, specutils, poliastro, yt, astroquery. NASA ADS API token and SIMBAD / TAP endpoints require network access. Some operations need HEASARC or IRSA archive downloads.
metadata:
  version: "1.0.0"
  skill-author: Scientific Agent Skills Contributors
  category: Physics & Astronomy
---

# Astrophysics

## Overview

Astrophysics in Python is dominated by the Astropy ecosystem: a single core package plus a stack of "affiliated" packages (photutils, specutils, poliastro, yt, astroquery) that interoperate through shared units, coordinates, time, and FITS I/O conventions. This skill covers the canonical flows: opening a FITS image, building a SkyCoord from an object name, performing aperture photometry, extracting and continuum-normalizing a 1-D spectrum, integrating an interplanetary orbit with poliastro, and visualizing a cosmological simulation with yt. It also covers cross-matching against SIMBAD, VizieR, and TAP services through astroquery.

## When to use this skill

- Open a FITS file and inspect headers, data, and WCS (World Coordinate System).
- Convert between sky coordinate systems (ICRS, Galactic, AltAz) for a target.
- Compute times in UTC, TDB, or TT and convert to/from Julian Date or ISO.
- Perform aperture or PSF photometry on a 2-D image with `photutils`.
- Read and normalize a 1-D spectrum with `specutils`.
- Integrate a Keplerian or N-body orbit with `poliastro`.
- Cross-match a local catalog against SIMBAD, VizieR, or a TAP service.
- Read and visualize an AMR cosmology snapshot with `yt`.
- Compute cosmological distances (luminosity, angular diameter) at a redshift.

## Prerequisites

- Python 3.10+ (3.11/3.12 supported).
- Core: `pip install astropy photutils specutils astroquery`.
- For orbits: `pip install poliastro` (uses `astropy` and `jplephem` for ephemerides).
- For AMR / cosmology: `pip install yt` (handles Enzo, Athena, FLASH, RAMSES, Gadget, Arepo).
- NASA ADS API: register at https://ui.adsabs.harvard.edu/ and export `ADS_DEV_KEY` env var.
- For SIMBAD / VizieR / TAP queries: outbound HTTPS to CDS Strasbourg.
- Optional: `pip install regions` for sky region masks; `pip install reproject` for image registration.
- Optional: `pip install sunpy` for solar physics (FITS I/O, light curves, helioviewer).
- 8 GB RAM minimum; 16 GB+ for processing large FITS mosaics or cosmological boxes.

## Core workflows

### Workflow 1: FITS I/O and WCS with astropy.io.fits

```python
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np

with fits.open("image.fits") as hdul:
    hdu = hdul[0]
    data = hdu.data.astype(np.float32)
    header = hdu.header
    wcs = WCS(header)
print(f"Image shape: {data.shape}, dtype: {data.dtype}")
print(f"Pixel scale: {wcs.proj_plane_pixel_scales()}")
ra, dec = wcs.all_pix2world([[256, 256]], 0)[0]
print(f"Pixel (256,256) -> RA={ra:.4f}, Dec={dec:.4f} deg")
```

Always close FITS files (use `with` or call `hdul.close()`); open file handles can corrupt the next write.

### Workflow 2: SkyCoord and time conversions

```python
from astropy.coordinates import SkyCoord, EarthLocation, AltAz
from astropy.time import Time
import astropy.units as u

# Object name -> ICRS coordinates
m42 = SkyCoord.from_name("M42")
print(f"M42 ICRS: {m42.ra.deg:.4f}, {m42.dec.deg:.4f}")
# Convert to Galactic
gal = m42.galactic
print(f"Galactic: l={gal.l.deg:.3f}, b={gal.b.deg:.3f}")

# Alt-Az at a specific observatory and time
keck = EarthLocation.of_site("Keck Observatory")
t = Time("2025-06-15T10:00:00", scale="utc")
altaz = m42.transform_to(AltAz(obstime=t, location=keck))
print(f"Alt={altaz.alt.deg:.2f}, Az={altaz.az.deg:.2f} at Keck on {t.iso}")

# Time conversions
print(f"JD: {t.jd:.5f}, MJD: {t.mjd:.5f}")
```

`SkyCoord.from_name` calls SIMBAD / VizieR / NED; cache results if used repeatedly.

### Workflow 3: Aperture photometry with photutils

```python
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.aperture import CircularAperture, CircularAnnulus, aperture_photometry
from photutils.detection import DAOStarFinder
import numpy as np

data = fits.getdata("image.fits")
mean, med, std = sigma_clipped_stats(data, sigma=3.0)
finder = DAOStarFinder(fwhm=3.0, threshold=5.0*std)
sources = finder(data - med)
print(f"Detected {len(sources)} sources")
positions = np.transpose((sources["xcentroid"], sources["ycentroid"]))
apertures = CircularAperture(positions, r=6.0)
annuli    = CircularAnnulus(positions, r_in=10.0, r_out=15.0)
phot = aperture_photometry(data, apertures)
bkg = aperture_photometry(data, annuli)
bkg_per_pix = bkg["aperture_sum"] / annuli.area
phot["flux"] = phot["aperture_sum"] - bkg_per_pix * apertures.area
print(phot["flux", "xcentroid", "ycentroid"][:5])
```

For crowded fields use `photutils.psf` (DAOGroup + PRF / EPSF) instead of aperture photometry.

### Workflow 4: 1-D spectroscopy with specutils

```python
from astropy.io import fits
from specutils import Spectrum1D, SpectrumList
import astropy.units as u
import numpy as np

# Open a 1-D calibrated spectrum from a FITS table
with fits.open("spec.fits") as hdul:
    tb = hdul[1].data
    wave = tb["WAVE"] * u.nm
    flux = tb["FLUX"] * u.Jy
    err  = tb["ERR"]  * u.Jy
spec = Spectrum1D(spectral_axis=wave, flux=flux, uncertainty=err)
print(f"Wavelength range: {spec.spectral_axis.min()} to {spec.spectral_axis.max()}")

# Convert to spectral flux density in different units
spec_fnu = spec.new_flux_unit(u.Unit("erg s-1 cm-2 Hz-1"))
# Normalize by continuum (median filter, low-order poly)
from specutils.manipulation import extract_region
from specutils.analysis import equivalent_width
snip = extract_region(spec_fnu, slice(0.3, 0.7))
ew = equivalent_width(snip)
print(f"Equivalent width: {ew:.3f}")
```

For ESO/VLT XSHOOTER or JWST/NIRSpec outputs, prefer the JWST pipeline products.

### Workflow 5: Orbital mechanics with poliastro

```python
from astropy.time import Time
from astropy import units as u
from poliastro.bodies import Earth
from poliastro.twobody import Orbit
from poliastro.ephem import Ephemerides

# ISS orbit: 6780 km semi-major axis, 51.6 deg inclination
iss = Orbit.from_classical(Earth,
        a=6780 << u.km, ecc=0.0006 << u.one,
        inc=51.6347 << u.deg, raan=0 << u.deg,
        argp=0 << u.deg, nu=0 << u.deg)
print(f"ISS period: {iss.period.to(u.min):.2f}")
print(f"ISS velocity: {iss.v.to(u.km/u.s)}")
# Propagate 1 hour
iss_future = iss.propagate(1 << u.h)
print(f"Position after 1h: {iss_future.r.to(u.km)}")
```

`propagate` uses the Keplerian analytic solution by default; switch to Cowell (`Orbit.to_ephem().sample`) for non-Keplerian perturbations.

### Workflow 6: Catalog cross-matching with astroquery

```python
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u

Simbad.add_votable_fields("ra","dec","sp_type","V")
obj = SkyCoord.from_name("Betelgeuse")
r = Simbad.query_region(obj, radius=30 << u.arcmin)
print(f"SIMBAD rows in 30 arcmin: {len(r)}")
print(r["MAIN_ID", "RA", "DEC", "SP_TYPE", "FLUX_V"][:5])

# Cross-match against Gaia DR3 in VizieR
v = Vizier(columns=["Source","RA_ICRS","DE_ICRS","Gmag","RPmag","BPmag"],
           column_filters={"Gmag":"<12"})
g = v.query_region(obj, radius=10 << u.arcmin, catalog="I/355/gaiadr3")
print(g[0][:5])
```

For TAP services, use `pyvo` (`pip install pyvo`): `pyvo.tap.TAPService(url).run_sync(...)`.

### Workflow 7: AMR cosmology visualization with yt

```python
import yt
ds = yt.load("RD0042/RD0042")
print(ds)
print(ds.field_list)
slc = yt.SlicePlot(ds, "x", ("gas","density"), width=(10,"Mpc"))
slc.set_log("gas density", True)
slc.save("slice_x.png")
# Phase plot: density vs temperature, weighted by cell mass
ph = yt.PhasePlot(ds.all_data(), ("gas","density"), ("gas","temperature"),
                  ("gas","mass"), weight=None)
ph.save("phase.png")
```

`yt` understands Enzo, Athena, AthenaPK, FLASH, RAMSES, Gadget, Arepo, and many more.

### Workflow 8: Cosmological distances

```python
from astropy.cosmology import Planck18, z_at_value
import astropy.units as u

z = 0.5
print(f"D_L(z={z}) = {Planck18.luminosity_distance(z):.2f}")
print(f"D_A(z={z}) = {Planck18.angular_diameter_distance(z):.2f}")
print(f"Age at z={z}: {Planck18.age(z):.3f}")
# Invert: redshift at luminosity distance 3 Gpc
z_back = z_at_value(Planck18.luminosity_distance, 3000 << u.Mpc)
print(f"z at D_L = 3 Gpc: {z_back:.4f}")
```

`Planck18` is the 2018 Planck cosmology. Switch to `WMAP9`, `Planck15`, or `FlatLambdaCDM(H0=70, Om0=0.3)` for alternatives.

## Best practices

- Use Astropy units everywhere; the run-time overhead is small and the unit-safety win is enormous.
- Cache remote queries (SIMBAD, VizieR, NASA ADS) to disk; networks fail and rate limits are real.
- Always specify `obstime` when transforming to AltAz or topocentric frames; the same coordinate gives different results at different times.
- For FITS files, prefer `memmap=True` (`fits.open(..., memmap=True)`) for files larger than RAM.
- Validate WCS by checking that the corners of the image map to sensible sky coordinates.
- Aperture photometry: subtract a local sky annulus, not the global image median, especially in nebular regions.
- For spectroscopy, plot the uncertainty envelope alongside the flux; a "feature" with S/N < 3 is not a detection.
- For orbital propagation, declare the frame and time scale (GCRS, TDB, TT) explicitly; mixing scales produces km-level errors over long arcs.
- Report photometric zero-points, filter transmission curves, and any color corrections used; reduced photometry without calibration is not reproducible.
- Use `units.Quantity` rather than raw floats in any function signature so callers cannot silently pass wrong units.

## Common pitfalls

- Treating FITS 1-indexed coordinates as 0-indexed in NumPy arrays; FITS pixels start at (1,1) but NumPy at (0,0). `wcs.all_pix2world(..., 0)` is correct for NumPy-style 0-indexed pixels.
- Forgetting to subtract the sky background before aperture photometry gives a constant offset of median*area per source.
- Using `SkyCoord(ra, dec)` without units: interpreted as degrees, which is usually wrong for catalog entries in degrees-minutes-seconds.
- Time scale mismatches: comparing a UTC observation to a TDB-predicted conjunction is off by ~60 seconds.
- Confusing heliocentric and topocentric redshifts; the difference is up to ~30 km/s depending on the target's ecliptic latitude.
- Reporting a discovery without checking catalog cross-matches in VizieR; many "new" objects are previously catalogued.
- Forgetting that Gaia DR3 `radial_velocity` is only reliable to ~100 km/s for stars with measured `radial_velocity_error < 5 km/s`.
- Mixing FITS header conventions for units (BUNIT keyword may say "Jy/beam" but the data may be in Jy/pixel); verify against the documentation.

## Worked example

Goal: For a target (Vega), look up its coordinates in SIMBAD, find nearby Gaia DR3 sources within 10 arcmin, plot the brightest 5 sources on the image, and compute their heliocentric distances.

```python
from astroquery.simbad import Simbad
from astroquery.vizier import Vizier
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.cosmology import Planck18
import matplotlib.pyplot as plt

Simbad.add_votable_fields("ra","dec","V")
vega = SkyCoord.from_name("Vega")
print(f"Vega ICRS: {vega.ra.deg:.5f}, {vega.dec.deg:+.5f}")

v = Vizier(columns=["Source","RA_ICRS","DE_ICRS","Gmag","Plx","Plx_err"],
           column_filters={"Gmag":"<10"}, row_limit=50)
g = v.query_region(vega, radius=10 << u.arcmin, catalog="I/355/gaiadr3")[0]
g.sort("Gmag")
top5 = g[:5]
print(top5["Source","Gmag","Plx","Plx_err"])

# Compute distances and uncertainties
parallax = top5["Plx"] << u.mas
parallax_err = top5["Plx_err"] << u.mas
distance = (1 / parallax.to(u.arcsec)).to(u.pc)
# A simple Gaussian error propagation (do not use for low S/N; use Bailer-Jones)
dist_err = (parallax_err / parallax) * distance
for src, d, e in zip(top5["Source"], distance, dist_err):
    print(f"{src}: {d.value:.1f} +/- {e.value:.1f} pc")

# Scatter plot of brightest 5 sources around Vega
coords = SkyCoord(ra=top5["RA_ICRS"], dec=top5["DE_ICRS"], unit="deg")
sep = vega.separation(coords).arcmin
plt.scatter(sep, top5["Gmag"], c="k")
plt.xlabel("Separation from Vega (arcmin)"); plt.ylabel("G magnitude")
plt.gca().invert_yaxis(); plt.savefig("vega_field.png", dpi=120)
```

## Tools and libraries

| Tool | Purpose | Install |
|---|---|---|
| astropy | Units, coordinates, time, FITS, WCS, cosmology | `pip install astropy` |
| photutils | Aperture and PSF photometry, detection | `pip install photutils` |
| specutils | 1-D spectroscopy, continuum normalization | `pip install specutils` |
| astroquery | SIMBAD, VizieR, IRSA, ADS, TAP queries | `pip install astroquery` |
| poliastro | Orbital mechanics, propagation, visualization | `pip install poliastro` |
| yt | AMR / N-body / SPH data, visualization | `pip install yt` |
| sunpy | Solar physics (light curves, AIA/HiFI I/O) | `pip install sunpy` |
| regions | Sky region masks for photometry | `pip install regions` |
| reproject | Reproject images between WCS frames | `pip install reproject` |
| pyvo | TAP / SIA / DALI service clients | `pip install pyvo` |
| jplephem | JPL ephemerides (used by astropy coordinates) | bundled with astropy |
| astroml | Statistical methods for astronomy | `pip install scikit-learn astroml` |

## References

- Astropy documentation: https://docs.astropy.org/
- photutils documentation: https://photutils.readthedocs.io/
- specutils documentation: https://specutils.readthedocs.io/
- astroquery documentation: https://astroquery.readthedocs.io/
- poliastro documentation: https://docs.poliastro.space/
- yt documentation: https://yt-project.org/doc/
- NASA ADS API: https://github.com/adsabs/adsabs-dev-api
- SIMBAD and VizieR at CDS: https://cds.unistra.fr/

## Ethics and safety

- Compute cost: Cross-matching a 1M-row local catalog against VizieR is heavy on the CDS servers; batch into chunks of 10k rows and add 0.5 s sleep between calls. Do not mirror the full Gaia archive locally; use TAP.
- Time-critical observations: Computed ephemerides for time-critical follow-up (e.g., target-of-opportunity for transients) must be checked against a second source; a wrong RA/Dec by an arcsecond can waste a night.
- Hazardous observation campaigns: Do not compute orbital predictions for potentially hazardous asteroids (PHAs) for the purpose of public alarm; ephemeris accuracy near Earth encounters requires MPC orbit-determination protocols that an agent prompt cannot replicate.
- Reproducibility: Always record the catalog version (e.g. "Gaia DR3"), the date of the query, and the query parameters (radius, filters, row limit) so a future analyst can reproduce the cross-match.
- Data attribution: Cite the underlying surveys (SDSS, 2MASS, Gaia, Planck) and CDS services in any publication that uses them; failure to cite is a breach of community norms.
- Telescope time: Computed observing windows and moon-phase requirements feed directly into proposals; misleading numbers waste oversubscribed time. Always validate with a mount-test before submitting.
- Privacy of discovery: A newly discovered transient or candidate should be reported to the relevant broker (TNS, Gaia alerts, MPC) before social media. The agent should encourage proper channels over public posting.
