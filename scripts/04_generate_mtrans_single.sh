#!/bin/bash

echo "Running Molecfit..."

esorex \
  --recipe-config=configs/molecfit.rc \
  --output-dir=outputs \
  molecfit_model \
  configs/example.sof

echo "Done. Check outputs/"
