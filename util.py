import numpy as np
from astropy.io import fits
from astropy.stats import sigma_clipped_stats
from photutils.detection import DAOStarFinder
from scipy import signal

from pathlib import Path

# converts the fits given in fit_list into arrays
def fits_to_array(fit_list):
    return np.array([np.float64(fits.getdata(fit_name, 0)) for fit_name in fit_list])


# creates the median of the given list
def create_master(frame_list, median=True):
    if np.shape(frame_list)[0] > 1:
        if median:
            master_frame = np.median(frame_list, axis=0)
        else:
            master_frame = np.mean(frame_list, axis=0)
    else:
        master_frame = frame_list[0]

    return master_frame


# user can choose pictures for the dark frame correction
def dark_correction(scidata, scidata_dark, quiet=False):
    masterdark = create_master(scidata_dark)
    scidata = scidata - masterdark

    return scidata


# creates a flat corrected scidata with raw scidata and the scidata from the flat-fits
def flat_correction(scidata, scidata_flats):
    masterflat = create_master(scidata_flats)
    medianflat = np.median(masterflat)

    masterflat /= medianflat

    scidata /= masterflat

    return scidata


def get_fits_names(path_to_fits: Path | str) -> list[Path]:
    return sorted(Path(path_to_fits).glob("*.fit?", case_sensitive=False))


def detect_star(n_stars_min, scidata, median, std, FWHM, ratio_gauss, factor_threshold):
    sources = []

    n_fits = scidata.shape[0]

    for i in range(n_fits):
        data = scidata[i, :, :]
        # init mask with True
        mask = np.ones(data.shape, dtype=bool)
        # set everything between 10 und -10 to False, i.e. not masked
        mask[10:-10, 10:-10] = False
        daofind = DAOStarFinder(threshold=factor_threshold * std[i], fwhm=FWHM, ratio=ratio_gauss, exclude_border=True, peakmax=48000)
        sources.append(daofind(data - median[i], mask=mask))

    for i in range(n_fits):
        sources[i].sort(['peak'])
        sources[i].reverse()

    list_stars = np.empty([0, 2])

    for i_fits in range(n_fits):
        for i_stars_new in range(len(sources[i_fits])):
            new_star_in_list = False
            for i_stars_old in range(len(list_stars)):
                if abs(sources[i_fits]['xcentroid'][i_stars_new] - list_stars[i_stars_old, 0]) <= 4 and abs(
                        sources[i_fits]['ycentroid'][i_stars_new] - list_stars[i_stars_old, 1]) <= 4:
                    new_star_in_list = True
                    break
            if not new_star_in_list:
                list_stars = np.r_[list_stars, np.array(
                    [[sources[i_fits]['xcentroid'][i_stars_new], sources[i_fits]['ycentroid'][i_stars_new]]])]

    star_in_fits = np.zeros((len(list_stars), n_fits), dtype=bool)

    for i_fits in range(n_fits):
        for i_star_list in range(len(list_stars)):
            for i_stars_fits in range(len(sources[i_fits])):
                if abs(sources[i_fits]['xcentroid'][i_stars_fits] - list_stars[i_star_list, 0]) <= 4 and abs(
                        sources[i_fits]['ycentroid'][i_stars_fits] - list_stars[i_star_list, 1]) <= 4:
                    star_in_fits[i_star_list, i_fits] = True
                    break

    list_star_new = np.empty([0, 2])

    for i_star in range(len(list_stars)):
        if not (False in star_in_fits[i_star, :]):
            list_star_new = np.r_[list_star_new, np.array([[list_stars[i_star, 0], list_stars[i_star, 1]]])]

    if len(list_star_new) < n_stars_min:
        print('')
        print(
            '##########################################################################################################################')
        print(
            'Not enough stars detected (%i). Please reduce the minimum number of stars or check input parameters like FWHM or threshold.' % len(
                list_star_new))
        print('Another possibility is that some of your images are bad and you have to remove them from the stack.')
        print(
            '##########################################################################################################################')
        print('')
        exit()
    else:
        n_stars_min = len(list_star_new)

    positions = np.zeros((n_fits, n_stars_min, 2))

    for i_star in range(n_stars_min):
        for i_fits in range(n_fits):
            for l in range(len(sources[i_fits])):
                if abs(sources[i_fits]['xcentroid'][l] - list_star_new[i_star, 0]) <= 4 and abs(
                        sources[i_fits]['ycentroid'][l] - list_star_new[i_star, 1]) <= 4:
                    positions[i_fits, i_star, 0] = sources[i_fits]['xcentroid'][l]
                    positions[i_fits, i_star, 1] = sources[i_fits]['ycentroid'][l]
                    break

    return sources, n_stars_min, positions


# for alignment of the stars -> offset
def get_offset(scidata, median, std, reference_fit=0):
    n_fits = scidata.shape[0]
    pixel = scidata.shape[1:]

    offset = np.zeros((n_fits, 2), dtype=int)
    scidata_threshold = np.zeros((n_fits, pixel[0], pixel[1]), dtype=np.float64)

    scidata_threshold[:, :, :] = scidata[:, :, :]

    for i in range(n_fits):
        scidata_threshold[i, scidata_threshold[i] < 16. * std[i] + median[i]] = 0
        scidata_threshold[i, scidata_threshold[i] >= 16. * std[i] + median[i]] = 1

        corr = signal.fftconvolve(scidata_threshold[reference_fit], scidata_threshold[i, ::-1, ::-1])
        offset[i, 0], offset[i, 1] = np.unravel_index(np.argmax(corr), corr.shape)

    reference = offset[reference_fit]
    offset = offset - reference

    return offset


def get_stats(scidata):
    if scidata.ndim == 3:
        n_fits = scidata.shape[0]
        mean, median, std = np.zeros((3, n_fits))

        for i in range(n_fits):
            mean[i], median[i], std[i] = sigma_clipped_stats(scidata[i, :, :], sigma=3.0)

    elif scidata.ndim == 2:
        mean, median, std = sigma_clipped_stats(scidata[:, :], sigma=3.0)

    return mean, median, std



# equalize the histogram for nicer display
#
def histeq(im, pixel, n_bins=2 ** 16):
    imhist, bins = np.histogram(im.flatten(), bins=range(n_bins - 1), density=False)

    imhist[0] = 0

    cdf = np.cumsum(imhist)  # cumulative distribution function
    im2 = np.zeros((len(im.flatten())))
    s = np.amin(cdf)
    j = 0
    for i in im.flatten():
        i = int(i)
        im2[j] = np.around(((cdf[i] - s) * (n_bins - 1) / (pixel[0] * pixel[1] - s)))
        j += 1
    im2 = im2 / np.amax(im2) * (2 ** 16 - 1)

    return np.array(im2, dtype=np.float64).reshape(im.shape)


# log stretch of the histogram for nicer display
#
def hist_log(image, scaling_factor=1000, n_bit=16):
    return (2 ** n_bit - 1) * np.log10(np.maximum(1e-100, scaling_factor * image / (2 ** n_bit - 1) + 1)) / np.log10(
        scaling_factor)
