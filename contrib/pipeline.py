import h5py


class HDF5Writer(Pipeline):
    """
    Class capable of writing daily OHLCV data to disk in a format that
    can be read efficiently by HDF5DailyBarReader.

    Parameters
    ----------
    filename : str
        The location at which we should write our output.
    date_chunk_size : int
        The number of days per chunk in the HDF5 file. If this is
        greater than the number of days in the data, the chunksize will
        match the actual number of days.

    See Also
    --------
    zipline.data.hdf5_daily_bars.HDF5DailyBarReader
    """
    VERSION = 0

    DATA = 'data'
    # INDEX = 'index'
    SCALING_FACTOR = 'scaling_factor'

    OPEN = 'open'
    HIGH = 'high'
    LOW = 'low'
    CLOSE = 'close'
    VOLUME = 'volume'

    FIELDS = (OPEN, HIGH, LOW, CLOSE, VOLUME)

    DEFAULT_SCALING_FACTORS = {
        # Retain 3 decimal places for prices.
        OPEN: 1000,
        HIGH: 1000,
        LOW: 1000,
        CLOSE: 1000,
        # Volume is expected to be a whole integer.
        VOLUME: 1,
    }

    def __init__(self, filename, date_chunk_size):
        self._filename = filename
        self._date_chunk_size = date_chunk_size

    def h5_file(self, mode):
        return h5py.File(self._filename, mode)

    def write(self,
              field,
              frames,
              scaling_factors=None):
        """
        Write the OHLCV data for one country to the HDF5 file.

        Parameters
        ----------
        frames : dict[str, pd.DataFrame]
            A dict mapping each OHLCV field to a dataframe with a row
            for each date and a column for each sid. The dataframes need
            to have the same index and columns.
        scaling_factors : dict[str, float], optional
            A dict mapping each OHLCV field to a scaling factor, which
            is applied (as a multiplier) to the values of field to
            efficiently store them as uint32, while maintaining desired
            precision. These factors are written to the file as metadata,
            which is consumed by the reader to adjust back to the original
            float values. Default is None, in which case
            DEFAULT_SCALING_FACTORS is used.
        """
        if scaling_factors is None:
            scaling_factors = self.DEFAULT_SCALING_FACTORS

        with self.h5_file(mode='a') as h5_file:
            # ensure that the file version has been written
            h5_file.attrs['version'] = self.VERSION

            # self._write_index_group(country_group, days, sids)
            field_group = h5_file.create_group(field)
            # sub_group
            self._write_data_group(
                field_group,
                frames,
                scaling_factors,
                chunks=None,
            )

    def write_from_sid_df_pairs(self,
                                field_code,
                                data,
                                currency_codes=None,
                                scaling_factors=None):
        """
        Parameters
        ----------
        country_code : str
            The ISO 3166 alpha-2 country code for this country.
        data : iterable[tuple[int, pandas.DataFrame]]
            The data chunks to write. Each chunk should be a tuple of
            sid and the data for that asset.
        currency_codes : pd.Series, optional
            Series mapping sids to 3-digit currency code values for those sids'
            listing currencies. If not passed, missing currencies will be
            written.
        scaling_factors : dict[str, float], optional
            A dict mapping each OHLCV field to a scaling factor, which
            is applied (as a multiplier) to the values of field to
            efficiently store them as uint32, while maintaining desired
            precision. These factors are written to the file as metadata,
            which is consumed by the reader to adjust back to the original
            float values. Default is None, in which case
            DEFAULT_SCALING_FACTORS is used.
        """
        data = list(data)
        if not data:
            empty_frame = pd.DataFrame(
                data=None,
                index=np.array([], dtype='datetime64[ns]'),
                columns=np.array([], dtype='int64'),
            )
            return self.write(
                {f: empty_frame.copy() for f in self.FIELDS},
                scaling_factors,
            )

        sids, frames = zip(*data)
        ohlcv_frame = pd.concat(frames)

        # Repeat each sid for each row in its corresponding frame.
        sid_ix = np.repeat(sids, [len(f) for f in frames])

        # Add id to the index, so the frame is indexed by (date, id).
        ohlcv_frame.set_index(sid_ix, append=True, inplace=True)

        frames = {
            field: ohlcv_frame[field].unstack()
            for field in self.FIELDS
        }

        return self.write(
            field_code,
            frames=frames,
            scaling_factors=scaling_factors,
        )

    def _write_data_group(self,
                          field_group,
                          frames,
                          scaling_factors,
                          chunks):
        """Write /country/data
        """
        data_group = field_group.create_group(self.DATA)

        for field in self.FIELDS:
            frame = frames[field]

            # Sort rows by increasing sid, and columns by increasing date.
            frame.sort_index(inplace=True)
            frame.sort_index(axis='columns', inplace=True)

            data = coerce_to_uint32(
                frame.T.fillna(0).values,
                scaling_factors[field],
            )

            dataset = data_group.create_dataset(
                field,
                compression='lzf',
                shuffle=True,
                data=data,
                chunks=chunks,
            )
            dataset.attrs[self.SCALING_FACTOR] = scaling_factors[field]

    def process_item(self, item, spider):
        owner = item['owner'][0]
        self.write(owner,item)
