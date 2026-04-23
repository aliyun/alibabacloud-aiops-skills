<a id="tensor-random"></a>

<a id="module-maxframe.tensor.random"></a>

# Random Sampling

## Sample random data

| [`maxframe.tensor.random.bytes`](generated/maxframe.tensor.random.bytes.md#maxframe.tensor.random.bytes)                               | Return random bytes.                                                  |
|----------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| [`maxframe.tensor.random.choice`](generated/maxframe.tensor.random.choice.md#maxframe.tensor.random.choice)                            | Generates a random sample from a given 1-D array                      |
| [`maxframe.tensor.random.permutation`](generated/maxframe.tensor.random.permutation.md#maxframe.tensor.random.permutation)             | Randomly permute a sequence, or return a permuted range.              |
| [`maxframe.tensor.random.rand`](generated/maxframe.tensor.random.rand.md#maxframe.tensor.random.rand)                                  | Random values in a given shape.                                       |
| [`maxframe.tensor.random.randint`](generated/maxframe.tensor.random.randint.md#maxframe.tensor.random.randint)                         | Return random integers from low (inclusive) to high (exclusive).      |
| [`maxframe.tensor.random.randn`](generated/maxframe.tensor.random.randn.md#maxframe.tensor.random.randn)                               | Return a sample (or samples) from the "standard normal" distribution. |
| [`maxframe.tensor.random.random_integers`](generated/maxframe.tensor.random.random_integers.md#maxframe.tensor.random.random_integers) | Random integers of type mt.int between low and high, inclusive.       |
| [`maxframe.tensor.random.random_sample`](generated/maxframe.tensor.random.random_sample.md#maxframe.tensor.random.random_sample)       | Return random floats in the half-open interval [0.0, 1.0).            |
| [`maxframe.tensor.random.random`](generated/maxframe.tensor.random.random.md#maxframe.tensor.random.random)                            | Return random floats in the half-open interval [0.0, 1.0).            |
| [`maxframe.tensor.random.ranf`](generated/maxframe.tensor.random.ranf.md#maxframe.tensor.random.ranf)                                  | Return random floats in the half-open interval [0.0, 1.0).            |
| [`maxframe.tensor.random.sample`](generated/maxframe.tensor.random.sample.md#maxframe.tensor.random.sample)                            | Return random floats in the half-open interval [0.0, 1.0).            |

## Distributions

| [`maxframe.tensor.random.beta`](generated/maxframe.tensor.random.beta.md#maxframe.tensor.random.beta)                                                 | Draw samples from a Beta distribution.                                                                                |
|-------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| [`maxframe.tensor.random.binomial`](generated/maxframe.tensor.random.binomial.md#maxframe.tensor.random.binomial)                                     | Draw samples from a binomial distribution.                                                                            |
| [`maxframe.tensor.random.chisquare`](generated/maxframe.tensor.random.chisquare.md#maxframe.tensor.random.chisquare)                                  | Draw samples from a chi-square distribution.                                                                          |
| [`maxframe.tensor.random.dirichlet`](generated/maxframe.tensor.random.dirichlet.md#maxframe.tensor.random.dirichlet)                                  | Draw samples from the Dirichlet distribution.                                                                         |
| [`maxframe.tensor.random.exponential`](generated/maxframe.tensor.random.exponential.md#maxframe.tensor.random.exponential)                            | Draw samples from an exponential distribution.                                                                        |
| [`maxframe.tensor.random.f`](generated/maxframe.tensor.random.f.md#maxframe.tensor.random.f)                                                          | Draw samples from an F distribution.                                                                                  |
| [`maxframe.tensor.random.gamma`](generated/maxframe.tensor.random.gamma.md#maxframe.tensor.random.gamma)                                              | Draw samples from a Gamma distribution.                                                                               |
| [`maxframe.tensor.random.geometric`](generated/maxframe.tensor.random.geometric.md#maxframe.tensor.random.geometric)                                  | Draw samples from the geometric distribution.                                                                         |
| [`maxframe.tensor.random.gumbel`](generated/maxframe.tensor.random.gumbel.md#maxframe.tensor.random.gumbel)                                           | Draw samples from a Gumbel distribution.                                                                              |
| [`maxframe.tensor.random.hypergeometric`](generated/maxframe.tensor.random.hypergeometric.md#maxframe.tensor.random.hypergeometric)                   | Draw samples from a Hypergeometric distribution.                                                                      |
| [`maxframe.tensor.random.laplace`](generated/maxframe.tensor.random.laplace.md#maxframe.tensor.random.laplace)                                        | Draw samples from the Laplace or double exponential distribution with specified location (or mean) and scale (decay). |
| [`maxframe.tensor.random.lognormal`](generated/maxframe.tensor.random.lognormal.md#maxframe.tensor.random.lognormal)                                  | Draw samples from a log-normal distribution.                                                                          |
| [`maxframe.tensor.random.logseries`](generated/maxframe.tensor.random.logseries.md#maxframe.tensor.random.logseries)                                  | Draw samples from a logarithmic series distribution.                                                                  |
| [`maxframe.tensor.random.multinomial`](generated/maxframe.tensor.random.multinomial.md#maxframe.tensor.random.multinomial)                            | Draw samples from a multinomial distribution.                                                                         |
| [`maxframe.tensor.random.multivariate_normal`](generated/maxframe.tensor.random.multivariate_normal.md#maxframe.tensor.random.multivariate_normal)    | Draw random samples from a multivariate normal distribution.                                                          |
| [`maxframe.tensor.random.negative_binomial`](generated/maxframe.tensor.random.negative_binomial.md#maxframe.tensor.random.negative_binomial)          | Draw samples from a negative binomial distribution.                                                                   |
| [`maxframe.tensor.random.noncentral_chisquare`](generated/maxframe.tensor.random.noncentral_chisquare.md#maxframe.tensor.random.noncentral_chisquare) | Draw samples from a noncentral chi-square distribution.                                                               |
| [`maxframe.tensor.random.noncentral_f`](generated/maxframe.tensor.random.noncentral_f.md#maxframe.tensor.random.noncentral_f)                         | Draw samples from the noncentral F distribution.                                                                      |
| [`maxframe.tensor.random.normal`](generated/maxframe.tensor.random.normal.md#maxframe.tensor.random.normal)                                           | Draw random samples from a normal (Gaussian) distribution.                                                            |
| [`maxframe.tensor.random.pareto`](generated/maxframe.tensor.random.pareto.md#maxframe.tensor.random.pareto)                                           | Draw samples from a Pareto II or Lomax distribution with specified shape.                                             |
| [`maxframe.tensor.random.poisson`](generated/maxframe.tensor.random.poisson.md#maxframe.tensor.random.poisson)                                        | Draw samples from a Poisson distribution.                                                                             |
| [`maxframe.tensor.random.power`](generated/maxframe.tensor.random.power.md#maxframe.tensor.random.power)                                              | Draws samples in [0, 1] from a power distribution with positive exponent a - 1.                                       |
| [`maxframe.tensor.random.rayleigh`](generated/maxframe.tensor.random.rayleigh.md#maxframe.tensor.random.rayleigh)                                     | Draw samples from a Rayleigh distribution.                                                                            |
| [`maxframe.tensor.random.standard_cauchy`](generated/maxframe.tensor.random.standard_cauchy.md#maxframe.tensor.random.standard_cauchy)                | Draw samples from a standard Cauchy distribution with mode = 0.                                                       |
| [`maxframe.tensor.random.standard_exponential`](generated/maxframe.tensor.random.standard_exponential.md#maxframe.tensor.random.standard_exponential) | Draw samples from the standard exponential distribution.                                                              |
| [`maxframe.tensor.random.standard_gamma`](generated/maxframe.tensor.random.standard_gamma.md#maxframe.tensor.random.standard_gamma)                   | Draw samples from a standard Gamma distribution.                                                                      |
| [`maxframe.tensor.random.standard_normal`](generated/maxframe.tensor.random.standard_normal.md#maxframe.tensor.random.standard_normal)                | Draw samples from a standard Normal distribution (mean=0, stdev=1).                                                   |
| [`maxframe.tensor.random.standard_t`](generated/maxframe.tensor.random.standard_t.md#maxframe.tensor.random.standard_t)                               | Draw samples from a standard Student's t distribution with df degrees of freedom.                                     |
| [`maxframe.tensor.random.triangular`](generated/maxframe.tensor.random.triangular.md#maxframe.tensor.random.triangular)                               | Draw samples from the triangular distribution over the interval `[left, right]`.                                      |
| [`maxframe.tensor.random.uniform`](generated/maxframe.tensor.random.uniform.md#maxframe.tensor.random.uniform)                                        | Draw samples from a uniform distribution.                                                                             |
| [`maxframe.tensor.random.vonmises`](generated/maxframe.tensor.random.vonmises.md#maxframe.tensor.random.vonmises)                                     | Draw samples from a von Mises distribution.                                                                           |
| [`maxframe.tensor.random.wald`](generated/maxframe.tensor.random.wald.md#maxframe.tensor.random.wald)                                                 | Draw samples from a Wald, or inverse Gaussian, distribution.                                                          |
| [`maxframe.tensor.random.weibull`](generated/maxframe.tensor.random.weibull.md#maxframe.tensor.random.weibull)                                        | Draw samples from a Weibull distribution.                                                                             |
| [`maxframe.tensor.random.zipf`](generated/maxframe.tensor.random.zipf.md#maxframe.tensor.random.zipf)                                                 | Draw samples from a Zipf distribution.                                                                                |

## Random number generator

| [`maxframe.tensor.random.seed`](generated/maxframe.tensor.random.seed.md#maxframe.tensor.random.seed)                      | Seed the generator.   |
|----------------------------------------------------------------------------------------------------------------------------|-----------------------|
| [`maxframe.tensor.random.RandomState`](generated/maxframe.tensor.random.RandomState.md#maxframe.tensor.random.RandomState) |                       |
