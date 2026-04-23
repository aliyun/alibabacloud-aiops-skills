# Special Functions

## Airy functions

| [`maxframe.tensor.special.airy`](generated/maxframe.tensor.special.airy.md#maxframe.tensor.special.airy)       | airy(z, out=None)   |
|----------------------------------------------------------------------------------------------------------------|---------------------|
| [`maxframe.tensor.special.airye`](generated/maxframe.tensor.special.airye.md#maxframe.tensor.special.airye)    | airye(z, out=None)  |
| [`maxframe.tensor.special.itairy`](generated/maxframe.tensor.special.itairy.md#maxframe.tensor.special.itairy) | itairy(x, out=None) |

## Information Theory functions

| [`maxframe.tensor.special.entr`](generated/maxframe.tensor.special.entr.md#maxframe.tensor.special.entr)             | Elementwise function for computing entropy.          |
|----------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| [`maxframe.tensor.special.rel_entr`](generated/maxframe.tensor.special.rel_entr.md#maxframe.tensor.special.rel_entr) | Elementwise function for computing relative entropy. |

## Bessel functions

| [`maxframe.tensor.special.jv`](generated/maxframe.tensor.special.jv.md#maxframe.tensor.special.jv)                   | jv(v, z, out=None)                                                     |
|----------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|
| [`maxframe.tensor.special.jve`](generated/maxframe.tensor.special.jve.md#maxframe.tensor.special.jve)                | jve(v, z, out=None)                                                    |
| [`maxframe.tensor.special.yn`](generated/maxframe.tensor.special.yn.md#maxframe.tensor.special.yn)                   | Bessel function of the second kind of integer order and real argument. |
| [`maxframe.tensor.special.yv`](generated/maxframe.tensor.special.yv.md#maxframe.tensor.special.yv)                   | yv(v, z, out=None)                                                     |
| [`maxframe.tensor.special.yve`](generated/maxframe.tensor.special.yve.md#maxframe.tensor.special.yve)                | yve(v, z, out=None)                                                    |
| [`maxframe.tensor.special.kn`](generated/maxframe.tensor.special.kn.md#maxframe.tensor.special.kn)                   | Modified Bessel function of the second kind of integer order n         |
| [`maxframe.tensor.special.kv`](generated/maxframe.tensor.special.kv.md#maxframe.tensor.special.kv)                   | kv(v, z, out=None)                                                     |
| [`maxframe.tensor.special.kve`](generated/maxframe.tensor.special.kve.md#maxframe.tensor.special.kve)                | kve(v, z, out=None)                                                    |
| [`maxframe.tensor.special.iv`](generated/maxframe.tensor.special.iv.md#maxframe.tensor.special.iv)                   | iv(v, z, out=None)                                                     |
| [`maxframe.tensor.special.ive`](generated/maxframe.tensor.special.ive.md#maxframe.tensor.special.ive)                | ive(v, z, out=None)                                                    |
| [`maxframe.tensor.special.hankel1`](generated/maxframe.tensor.special.hankel1.md#maxframe.tensor.special.hankel1)    | hankel1(v, z, out=None)                                                |
| [`maxframe.tensor.special.hankel1e`](generated/maxframe.tensor.special.hankel1e.md#maxframe.tensor.special.hankel1e) | hankel1e(v, z, out=None)                                               |
| [`maxframe.tensor.special.hankel2`](generated/maxframe.tensor.special.hankel2.md#maxframe.tensor.special.hankel2)    | hankel2(v, z, out=None)                                                |
| [`maxframe.tensor.special.hankel2e`](generated/maxframe.tensor.special.hankel2e.md#maxframe.tensor.special.hankel2e) | hankel2e(v, z, out=None)                                               |

## Error functions and fresnel integrals

| [`maxframe.tensor.special.erf`](generated/maxframe.tensor.special.erf.md#maxframe.tensor.special.erf)                         | Returns the error function of complex argument.             |
|-------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------|
| [`maxframe.tensor.special.erfc`](generated/maxframe.tensor.special.erfc.md#maxframe.tensor.special.erfc)                      | Complementary error function, `1 - erf(x)`.                 |
| [`maxframe.tensor.special.erfcx`](generated/maxframe.tensor.special.erfcx.md#maxframe.tensor.special.erfcx)                   | Scaled complementary error function, `exp(x**2) * erfc(x)`. |
| [`maxframe.tensor.special.erfi`](generated/maxframe.tensor.special.erfi.md#maxframe.tensor.special.erfi)                      | Imaginary error function, `-i erf(i z)`.                    |
| [`maxframe.tensor.special.erfinv`](generated/maxframe.tensor.special.erfinv.md#maxframe.tensor.special.erfinv)                | Inverse of the error function.                              |
| [`maxframe.tensor.special.erfcinv`](generated/maxframe.tensor.special.erfcinv.md#maxframe.tensor.special.erfcinv)             | Inverse of the complementary error function.                |
| [`maxframe.tensor.special.wofz`](generated/maxframe.tensor.special.wofz.md#maxframe.tensor.special.wofz)                      | Faddeeva function                                           |
| [`maxframe.tensor.special.dawsn`](generated/maxframe.tensor.special.dawsn.md#maxframe.tensor.special.dawsn)                   | Dawson's integral.                                          |
| [`maxframe.tensor.special.fresnel`](generated/maxframe.tensor.special.fresnel.md#maxframe.tensor.special.fresnel)             | Fresnel integrals.                                          |
| [`maxframe.tensor.special.modfresnelp`](generated/maxframe.tensor.special.modfresnelp.md#maxframe.tensor.special.modfresnelp) | modfresnelp(x, out=None)                                    |
| [`maxframe.tensor.special.modfresnelm`](generated/maxframe.tensor.special.modfresnelm.md#maxframe.tensor.special.modfresnelm) | modfresnelm(x, out=None)                                    |

## Ellipsoidal harmonics

| [`maxframe.tensor.special.ellip_harm`](generated/maxframe.tensor.special.ellip_harm.md#maxframe.tensor.special.ellip_harm)       | Ellipsoidal harmonic functions E^p_n(l)                |
|----------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------|
| [`maxframe.tensor.special.ellip_harm_2`](generated/maxframe.tensor.special.ellip_harm_2.md#maxframe.tensor.special.ellip_harm_2) | Ellipsoidal harmonic functions F^p_n(l)                |
| [`maxframe.tensor.special.ellip_normal`](generated/maxframe.tensor.special.ellip_normal.md#maxframe.tensor.special.ellip_normal) | Ellipsoidal harmonic normalization constants gamma^p_n |

## Elliptic functions and integrals

| [`maxframe.tensor.special.ellipk`](generated/maxframe.tensor.special.ellipk.md#maxframe.tensor.special.ellipk)          | Complete elliptic integral of the first kind.              |
|-------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| [`maxframe.tensor.special.ellipkm1`](generated/maxframe.tensor.special.ellipkm1.md#maxframe.tensor.special.ellipkm1)    | Complete elliptic integral of the first kind around m = 1  |
| [`maxframe.tensor.special.ellipkinc`](generated/maxframe.tensor.special.ellipkinc.md#maxframe.tensor.special.ellipkinc) | Incomplete elliptic integral of the first kind             |
| [`maxframe.tensor.special.ellipe`](generated/maxframe.tensor.special.ellipe.md#maxframe.tensor.special.ellipe)          | Complete elliptic integral of the second kind              |
| [`maxframe.tensor.special.ellipeinc`](generated/maxframe.tensor.special.ellipeinc.md#maxframe.tensor.special.ellipeinc) | Incomplete elliptic integral of the second kind            |
| [`maxframe.tensor.special.elliprc`](generated/maxframe.tensor.special.elliprc.md#maxframe.tensor.special.elliprc)       | Degenerate symmetric elliptic integral.                    |
| [`maxframe.tensor.special.elliprf`](generated/maxframe.tensor.special.elliprf.md#maxframe.tensor.special.elliprf)       | Completely-symmetric elliptic integral of the first kind.  |
| [`maxframe.tensor.special.elliprg`](generated/maxframe.tensor.special.elliprg.md#maxframe.tensor.special.elliprg)       | Completely-symmetric elliptic integral of the second kind. |
| [`maxframe.tensor.special.elliprj`](generated/maxframe.tensor.special.elliprj.md#maxframe.tensor.special.elliprj)       | Symmetric elliptic integral of the third kind.             |

## Gamma and related functions

| [`maxframe.tensor.special.gamma`](generated/maxframe.tensor.special.gamma.md#maxframe.tensor.special.gamma)                      | gamma(z, out=None)                                                                  |
|----------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------|
| [`maxframe.tensor.special.gammaln`](generated/maxframe.tensor.special.gammaln.md#maxframe.tensor.special.gammaln)                | Logarithm of the absolute value of the Gamma function.                              |
| [`maxframe.tensor.special.loggamma`](generated/maxframe.tensor.special.loggamma.md#maxframe.tensor.special.loggamma)             | loggamma(z, out=None)                                                               |
| [`maxframe.tensor.special.gammasgn`](generated/maxframe.tensor.special.gammasgn.md#maxframe.tensor.special.gammasgn)             | Sign of the gamma function.                                                         |
| [`maxframe.tensor.special.gammainc`](generated/maxframe.tensor.special.gammainc.md#maxframe.tensor.special.gammainc)             | Regularized lower incomplete gamma function.                                        |
| [`maxframe.tensor.special.gammaincinv`](generated/maxframe.tensor.special.gammaincinv.md#maxframe.tensor.special.gammaincinv)    | Inverse to the regularized lower incomplete gamma function.                         |
| [`maxframe.tensor.special.gammaincc`](generated/maxframe.tensor.special.gammaincc.md#maxframe.tensor.special.gammaincc)          | Regularized lower incomplete gamma function.                                        |
| [`maxframe.tensor.special.gammainccinv`](generated/maxframe.tensor.special.gammainccinv.md#maxframe.tensor.special.gammainccinv) | Inverse of the regularized upper incomplete gamma function.                         |
| [`maxframe.tensor.special.beta`](generated/maxframe.tensor.special.beta.md#maxframe.tensor.special.beta)                         | Beta function.                                                                      |
| [`maxframe.tensor.special.betaln`](generated/maxframe.tensor.special.betaln.md#maxframe.tensor.special.betaln)                   | Natural logarithm of absolute value of beta function.                               |
| [`maxframe.tensor.special.betainc`](generated/maxframe.tensor.special.betainc.md#maxframe.tensor.special.betainc)                | Regularized incomplete beta function.                                               |
| [`maxframe.tensor.special.betaincinv`](generated/maxframe.tensor.special.betaincinv.md#maxframe.tensor.special.betaincinv)       | Inverse of the regularized incomplete beta function.                                |
| [`maxframe.tensor.special.psi`](generated/maxframe.tensor.special.psi.md#maxframe.tensor.special.psi)                            | psi(z, out=None)                                                                    |
| [`maxframe.tensor.special.rgamma`](generated/maxframe.tensor.special.rgamma.md#maxframe.tensor.special.rgamma)                   | rgamma(z, out=None)                                                                 |
| [`maxframe.tensor.special.polygamma`](generated/maxframe.tensor.special.polygamma.md#maxframe.tensor.special.polygamma)          | Polygamma functions.                                                                |
| [`maxframe.tensor.special.multigammaln`](generated/maxframe.tensor.special.multigammaln.md#maxframe.tensor.special.multigammaln) | Returns the log of multivariate gamma, also sometimes called the generalized gamma. |
| [`maxframe.tensor.special.digamma`](generated/maxframe.tensor.special.digamma.md#maxframe.tensor.special.digamma)                | psi(z, out=None)                                                                    |
| [`maxframe.tensor.special.poch`](generated/maxframe.tensor.special.poch.md#maxframe.tensor.special.poch)                         | Pochhammer symbol.                                                                  |

## Sigmoidal functions

| [`maxframe.tensor.special.expit`](generated/maxframe.tensor.special.expit.md#maxframe.tensor.special.expit)             | expit(x, out=None)     |
|-------------------------------------------------------------------------------------------------------------------------|------------------------|
| [`maxframe.tensor.special.log_expit`](generated/maxframe.tensor.special.log_expit.md#maxframe.tensor.special.log_expit) | log_expit(x, out=None) |
| [`maxframe.tensor.special.logit`](generated/maxframe.tensor.special.logit.md#maxframe.tensor.special.logit)             |                        |

## Other special functions

| [`maxframe.tensor.special.softmax`](generated/maxframe.tensor.special.softmax.md#maxframe.tensor.special.softmax)    | Compute the softmax function. The softmax function transforms each element of a collection by computing the exponential of each element divided by the sum of the exponentials of all the elements. That is, if x is a one-dimensional numpy array::.   |
|----------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [`maxframe.tensor.special.softplus`](generated/maxframe.tensor.special.softplus.md#maxframe.tensor.special.softplus) | Compute the softplus function element-wise.                                                                                                                                                                                                             |

## Convenience functions

| [`maxframe.tensor.special.xlogy`](generated/maxframe.tensor.special.xlogy.md#maxframe.tensor.special.xlogy)   | Compute `x*log(y)` so that the result is 0 if `x = 0`.   |
|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
