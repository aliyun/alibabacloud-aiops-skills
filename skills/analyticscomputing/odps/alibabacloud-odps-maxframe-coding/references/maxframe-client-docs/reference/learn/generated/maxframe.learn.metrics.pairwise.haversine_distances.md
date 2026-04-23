# maxframe.learn.metrics.pairwise.haversine_distances

### maxframe.learn.metrics.pairwise.haversine_distances(X, Y=None)

Compute the Haversine distance between samples in X and Y

The Haversine (or great circle) distance is the angular distance between
two points on the surface of a sphere. The first distance of each point is
assumed to be the latitude, the second is the longitude, given in radians.
The dimension of the data must be 2.

$$
D(x, y) = 2\arcsin[\sqrt{\sin^2((x1 - y1) / 2)
                         + \cos(x1)\cos(y1)\sin^2((x2 - y2) / 2)}]

$$

* **Parameters:**
  * **X** (*array_like* *,* *shape* *(**n_samples_1* *,* *2* *)*)
  * **Y** (*array_like* *,* *shape* *(**n_samples_2* *,* *2* *)* *,* *optional*)
* **Returns:**
  **distance**
* **Return type:**
  {Tensor}, shape (n_samples_1, n_samples_2)

### Notes

As the Earth is nearly spherical, the haversine formula provides a good
approximation of the distance between two points of the Earth surface, with
a less than 1% error on average.

### Examples

We want to calculate the distance between the Ezeiza Airport
(Buenos Aires, Argentina) and the Charles de Gaulle Airport (Paris, France)

```pycon
>>> from maxframe.learn.metrics.pairwise import haversine_distances
>>> bsas = [-34.83333, -58.5166646]
>>> paris = [49.0083899664, 2.53844117956]
>>> result = haversine_distances([bsas, paris])
>>> (result * 6371000/1000).execute()  # multiply by Earth radius to get kilometers
array([[    0.        , 11279.45379464],
       [11279.45379464,     0.        ]])
```
