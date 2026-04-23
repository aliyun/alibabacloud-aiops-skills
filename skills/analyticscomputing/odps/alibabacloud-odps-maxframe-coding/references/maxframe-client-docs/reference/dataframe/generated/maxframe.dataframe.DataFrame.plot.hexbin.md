# maxframe.dataframe.DataFrame.plot.hexbin

#### DataFrame.plot.hexbin(\*args, \*\*kwargs)

Generate a hexagonal binning plot.

Generate a hexagonal binning plot of x versus y. If C is None
(the default), this is a histogram of the number of occurrences
of the observations at `(x[i], y[i])`.

If C is specified, specifies values at given coordinates
`(x[i], y[i])`. These values are accumulated for each hexagonal
bin and then reduced according to reduce_C_function,
having as default the NumPy’s mean function (`numpy.mean()`).
(If C is specified, it must also be a 1-D sequence
of the same length as x and y, or a column label.)

* **Parameters:**
  * **x** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The column label or position for x points.
  * **y** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The column label or position for y points.
  * **C** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*str*](https://docs.python.org/3/library/stdtypes.html#str) *,* *optional*) – The column label or position for the value of (x, y) point.
  * **reduce_C_function** (callable, default np.mean) – Function of one argument that reduces all the values in a bin to
    a single number (e.g. np.mean, np.max, np.sum, np.std).
  * **gridsize** ([*int*](https://docs.python.org/3/library/functions.html#int) *or* [*tuple*](https://docs.python.org/3/library/stdtypes.html#tuple) *of*  *(*[*int*](https://docs.python.org/3/library/functions.html#int) *,* [*int*](https://docs.python.org/3/library/functions.html#int) *)* *,* *default 100*) – The number of hexagons in the x-direction.
    The corresponding number of hexagons in the y-direction is
    chosen in a way that the hexagons are approximately regular.
    Alternatively, gridsize can be a tuple with two elements
    specifying the number of hexagons in the x-direction and the
    y-direction.
  * **\*\*kwargs** – Additional keyword arguments are documented in
    [`DataFrame.plot()`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot).
* **Returns:**
  The matplotlib `Axes` on which the hexbin is plotted.
* **Return type:**
  matplotlib.AxesSubplot

#### SEE ALSO
[`DataFrame.plot`](maxframe.dataframe.DataFrame.plot.md#maxframe.dataframe.DataFrame.plot)
: Make plots of a DataFrame.

[`matplotlib.pyplot.hexbin`](https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.hexbin.html#matplotlib.pyplot.hexbin)
: Hexagonal binning plot using matplotlib, the matplotlib function that is used under the hood.

### Examples

The following examples are generated with random data from
a normal distribution.

The next example uses C and np.sum as reduce_C_function.
Note that ‘observations’ values ranges from 1 to 5 but the result
plot shows values up to more than 25. This is because of the
reduce_C_function.
