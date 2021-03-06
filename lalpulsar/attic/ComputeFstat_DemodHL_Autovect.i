//
// Copyright (C) 2007, 2008, 2009, 2010, 2012 Bernd Machenschalk, Reinhard Prix
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with with program; see the file COPYING. If not, write to the
// Free Software Foundation, Inc., 59 Temple Place, Suite 330, Boston,
// MA  02111-1307  USA
//

/* designed for four vector elemens (ve) as there are in SSE and AltiVec */
/* vectorizes with gcc-4.2.3 and gcc-4.1.3 */
{
  {
    /* the initialization already handles the first elements,
       thus there are only 7 loop iterations left */
    UINT4 l;
    UINT4 ve;
    REAL4 *Xal   = (REAL4*)Xalpha_l;
    REAL4 STn[4] = {Xal[0],Xal[1],Xal[2],Xal[3]};
    REAL4 kappa_max = kappa_star + 1.0f * DTERMS - 1.0f;
    REAL4 pn[4]  = {kappa_max, kappa_max, kappa_max-1.0f, kappa_max-1.0f};
    REAL4 qn[4];

    for ( ve = 0; ve < 4; ve++)
      qn[ve] = pn[ve];

    for ( l = 1; l < DTERMS; l ++ ) {
      Xal += 4;
      for ( ve = 0; ve < 4; ve++) {
        pn[ve] -= 2.0f;
        STn[ve] = pn[ve] * STn[ve] + qn[ve] * Xal[ve];
        qn[ve] *= pn[ve];
      }
    }

    REAL4 s_alpha, c_alpha;   /* sin(2pi kappa_alpha) and (cos(2pi kappa_alpha)-1) */
    XLALSinCos2PiLUTtrimmed( &s_alpha, &c_alpha, kappa_star );
    c_alpha -= 1.0f;

    /* combine the partial sums: */
    {
#if EAH_HOTLOOP_DIVS == EAH_HOTLOOP_DIVS_RECIPROCAL
      /* if the division is to be done outside the SIMD unit */

      REAL4 r_qn  = 1.0 / (qn[0] * qn[2]);
      REAL4 U_alpha = (STn[0] * qn[2] + STn[2] * qn[0]) * r_qn;
      REAL4 V_alpha = (STn[1] * qn[3] + STn[3] * qn[1]) * r_qn;

      realXP = s_alpha * U_alpha - c_alpha * V_alpha;
      imagXP = c_alpha * U_alpha + s_alpha * V_alpha;

#else /* EAH_HOTLOOP_DIVS */
      /* if the division can and should be done inside the SIMD unit */

      REAL4 U_alpha, V_alpha;

      for ( ve = 0; ve < 4; ve++)
        STn[ve] /= qn[ve];

      U_alpha = (STn[0] + STn[2]);
      V_alpha = (STn[1] + STn[3]);

      realXP = s_alpha * U_alpha - c_alpha * V_alpha;
      imagXP = c_alpha * U_alpha + s_alpha * V_alpha;

#endif /* EAH_HOTLOOP_DIVS */
    }
  }

  XLALSinCos2PiLUT( &imagQ, &realQ, lambda_alpha );
}
