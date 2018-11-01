// $Id
//
// NNPDF++ 2013
//
// Authors: Nathan Hartland,  n.p.hartland@ed.ac.uk
//          Stefano Carrazza, stefano.carrazza@mi.infn.it
//          Luigi Del Debbio, luigi.del.debbio@ed.ac.uk

#pragma once

#include "buildmaster_utils.h"

class SHIPNUFilter: public CommonData
{
public: SHIPNUFilter():
  CommonData("SHIPNU") { ReadData(); }

private:
  void ReadData();
};

class SHIPNBFilter: public CommonData
{
public: SHIPNBFilter():
  CommonData("SHIPNB") { ReadData(); }

private:
  void ReadData();
};
