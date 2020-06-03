/**
 * INT.cc
 * Integrability observables
 */

#include "INT.h"
#include <array>

void register_integrability(vector<CommonData*>& list)
{
  // Integrability sets
  const std::array<std::string, 6>  INTsets = { 
    "INTEGXT3",
    "INTEGXT8",
    "INTEGXT15",
    "INTEGXV",
    "INTEGXV3",
    "INTEGXV8"};

  for (auto set : INTsets)
    list.push_back(new IntFilter(set));
}

void IntFilter::ReadData()
{
  const double q2int = 2.7225; //GeV2

  fKin1[0] = 1e-7;
  fKin1[1] = 1e-6;
  fKin1[2] = 1e-5;

  for (int i=0; i< fNData; i++)
  {
    fData[i] = 0;
    fStat[i] = 0;
    fKin2[i] = q2int;
    fKin3[i] = 0;
  }

}
