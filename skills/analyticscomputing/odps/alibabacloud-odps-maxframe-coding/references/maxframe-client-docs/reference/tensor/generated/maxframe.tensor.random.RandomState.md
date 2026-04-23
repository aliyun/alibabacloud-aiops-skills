# maxframe.tensor.random.RandomState

### *class* maxframe.tensor.random.RandomState(seed=None)

#### \_\_init_\_(seed=None)

### Methods

| [`__init__`](#maxframe.tensor.random.RandomState.__init__)([seed])   |                                                                                                                       |
|----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| `beta`(a, b[, size, chunk_size, gpu, dtype])                         | Draw samples from a Beta distribution.                                                                                |
| `binomial`(n, p[, size, chunk_size, gpu, dtype])                     | Draw samples from a binomial distribution.                                                                            |
| `bytes`(length)                                                      | Return random bytes.                                                                                                  |
| `chisquare`(df[, size, chunk_size, gpu, dtype])                      | Draw samples from a chi-square distribution.                                                                          |
| `choice`(a[, size, replace, p, chunk_size, gpu])                     | Generates a random sample from a given 1-D array                                                                      |
| `dirichlet`(alpha[, size, chunk_size, gpu, dtype])                   | Draw samples from the Dirichlet distribution.                                                                         |
| `exponential`([scale, size, chunk_size, gpu, ...])                   | Draw samples from an exponential distribution.                                                                        |
| `f`(dfnum, dfden[, size, chunk_size, gpu, dtype])                    | Draw samples from an F distribution.                                                                                  |
| `from_numpy`(np_random_state)                                        |                                                                                                                       |
| `gamma`(shape[, scale, size, chunk_size, gpu, ...])                  | Draw samples from a Gamma distribution.                                                                               |
| `geometric`(p[, size, chunk_size, gpu, dtype])                       | Draw samples from the geometric distribution.                                                                         |
| `gumbel`([loc, scale, size, chunk_size, gpu, ...])                   | Draw samples from a Gumbel distribution.                                                                              |
| `hypergeometric`(ngood, nbad, nsample[, size, ...])                  | Draw samples from a Hypergeometric distribution.                                                                      |
| `laplace`([loc, scale, size, chunk_size, gpu, ...])                  | Draw samples from the Laplace or double exponential distribution with specified location (or mean) and scale (decay). |
| `logistic`([loc, scale, size, chunk_size, ...])                      | Draw samples from a logistic distribution.                                                                            |
| `lognormal`([mean, sigma, size, chunk_size, ...])                    | Draw samples from a log-normal distribution.                                                                          |
| `logseries`(p[, size, chunk_size, gpu, dtype])                       | Draw samples from a logarithmic series distribution.                                                                  |
| `multinomial`(n, pvals[, size, chunk_size, ...])                     | Draw samples from a multinomial distribution.                                                                         |
| `multivariate_normal`(mean, cov[, size, ...])                        | Draw random samples from a multivariate normal distribution.                                                          |
| `negative_binomial`(n, p[, size, chunk_size, ...])                   | Draw samples from a negative binomial distribution.                                                                   |
| `noncentral_chisquare`(df, nonc[, size, ...])                        | Draw samples from a noncentral chi-square distribution.                                                               |
| `noncentral_f`(dfnum, dfden, nonc[, size, ...])                      | Draw samples from the noncentral F distribution.                                                                      |
| `normal`([loc, scale, size, chunk_size, gpu, ...])                   | Draw random samples from a normal (Gaussian) distribution.                                                            |
| `pareto`(a[, size, chunk_size, gpu, dtype])                          | Draw samples from a Pareto II or Lomax distribution with specified shape.                                             |
| `permutation`(x[, axis, chunk_size])                                 | Randomly permute a sequence, or return a permuted range.                                                              |
| `poisson`([lam, size, chunk_size, gpu, dtype])                       | Draw samples from a Poisson distribution.                                                                             |
| `power`(a[, size, chunk_size, gpu, dtype])                           | Draws samples in [0, 1] from a power distribution with positive exponent a - 1.                                       |
| `rand`(\*dn, \*\*kw)                                                 | Random values in a given shape.                                                                                       |
| `randint`(low[, high, size, dtype, density, ...])                    | Return random integers from low (inclusive) to high (exclusive).                                                      |
| `randn`(\*dn, \*\*kw)                                                | Return a sample (or samples) from the "standard normal" distribution.                                                 |
| `random`([size, chunk_size, gpu, dtype])                             | Return random floats in the half-open interval [0.0, 1.0).                                                            |
| `random_integers`(low[, high, size, ...])                            | Random integers of type mt.int between low and high, inclusive.                                                       |
| `random_sample`([size, chunk_size, gpu, dtype])                      | Return random floats in the half-open interval [0.0, 1.0).                                                            |
| `ranf`([size, chunk_size, gpu, dtype])                               | Return random floats in the half-open interval [0.0, 1.0).                                                            |
| `rayleigh`([scale, size, chunk_size, gpu, dtype])                    | Draw samples from a Rayleigh distribution.                                                                            |
| `sample`([size, chunk_size, gpu, dtype])                             | Return random floats in the half-open interval [0.0, 1.0).                                                            |
| `seed`([seed])                                                       | Seed the generator.                                                                                                   |
| `shuffle`(x[, axis])                                                 | Modify a sequence in-place by shuffling its contents.                                                                 |
| `standard_cauchy`([size, chunk_size, gpu, dtype])                    | Draw samples from a standard Cauchy distribution with mode = 0.                                                       |
| `standard_exponential`([size, chunk_size, ...])                      | Draw samples from the standard exponential distribution.                                                              |
| `standard_gamma`(shape[, size, chunk_size, ...])                     | Draw samples from a standard Gamma distribution.                                                                      |
| `standard_normal`([size, chunk_size, gpu, dtype])                    | Draw samples from a standard Normal distribution (mean=0, stdev=1).                                                   |
| `standard_t`(df[, size, chunk_size, gpu, dtype])                     | Draw samples from a standard Student's t distribution with df degrees of freedom.                                     |
| `to_numpy`()                                                         |                                                                                                                       |
| `triangular`(left, mode, right[, size, ...])                         | Draw samples from the triangular distribution over the interval `[left, right]`.                                      |
| `uniform`([low, high, size, chunk_size, gpu, ...])                   | Draw samples from a uniform distribution.                                                                             |
| `vonmises`(mu, kappa[, size, chunk_size, gpu, ...])                  | Draw samples from a von Mises distribution.                                                                           |
| `wald`(mean, scale[, size, chunk_size, gpu, dtype])                  | Draw samples from a Wald, or inverse Gaussian, distribution.                                                          |
| `weibull`(a[, size, chunk_size, gpu, dtype])                         | Draw samples from a Weibull distribution.                                                                             |
| `zipf`(a[, size, chunk_size, gpu, dtype])                            | Draw samples from a Zipf distribution.                                                                                |
