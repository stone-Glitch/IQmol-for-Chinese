/*******************************************************************************

  Copyright (C) 2022 Andrew Gilbert

  This file is part of IQmol, a free molecular visualization program. See
  <http://iqmol.org> for more details.

  IQmol is free software: you can redistribute it and/or modify it under the
  terms of the GNU General Public License as published by the Free Software
  Foundation, either version 3 of the License, or (at your option) any later
  version.

  IQmol is distributed in the hope that it will be useful, but WITHOUT ANY
  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
  FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
  details.

  You should have received a copy of the GNU General Public License along
  with IQmol.  If not, see <http://www.gnu.org/licenses/>.

********************************************************************************/

#include "SurfaceType.h"
#include <QCoreApplication>
#include <QDebug>


namespace IQmol {
namespace Data {


SurfaceType::SurfaceType(int const kind)
{
   switch (kind) {  
      case Custom:                  m_kind = Custom;                  break;
      case AlphaOrbital:            m_kind = AlphaOrbital;            break;
      case BetaOrbital:             m_kind = BetaOrbital;             break;
      case TotalDensity:            m_kind = TotalDensity;            break;
      case SpinDensity:             m_kind = SpinDensity;             break;
      case AlphaDensity:            m_kind = AlphaDensity;            break;
      case BetaDensity:             m_kind = BetaDensity;             break;
      case DensityCombo:            m_kind = DensityCombo;            break;
      case CubeData:                m_kind = CubeData;                break;
      case VanDerWaals:             m_kind = VanDerWaals;             break;
      case Promolecule:             m_kind = Promolecule;             break;
      case SolventExcluded:         m_kind = SolventExcluded;         break;
      case SID:                     m_kind = SID;                     break;
      case ElectrostaticPotential:  m_kind = ElectrostaticPotential;  break;
      case Geminal:                 m_kind = Geminal;                 break;
      case Correlation:             m_kind = Correlation;             break;
      case CustomDensity:           m_kind = CustomDensity;           break;
      case BasisFunction:           m_kind = BasisFunction;           break;
      case DysonLeft:               m_kind = DysonLeft;               break;
      case DysonRight:              m_kind = DysonRight;              break;
      case MullikenAtomic:          m_kind = MullikenAtomic;          break;
      case MullikenDiatomic:        m_kind = MullikenDiatomic;        break;
      case GenericOrbital:          m_kind = GenericOrbital;          break;
      case Ribbon:                  m_kind = Ribbon;                  break;

      case AlphaRealOrbital:        m_kind = AlphaRealOrbital;        break;
      case AlphaImaginaryOrbital:   m_kind = AlphaImaginaryOrbital;   break;
      case BetaRealOrbital:         m_kind = BetaRealOrbital;         break;
      case BetaImaginaryOrbital:    m_kind = BetaImaginaryOrbital;    break;

      default:
         qDebug() << "Unknown surface type" << kind;
         m_kind = Custom;
   }
}



SurfaceType::Units SurfaceType::units() const
{
   Units units(Orbital);

   if (isDensity() || 
       m_kind == SID || 
       m_kind == Promolecule ||
       m_kind == SolventExcluded || 
       m_kind == ElectrostaticPotential || 
       m_kind == VanDerWaals) {
       units = Volume;
   }

   return units;
}



QString SurfaceType::toString() const 
{
   QString label;
   switch (m_kind) {
      case Custom:                 label = m_label;                   break;
      case AlphaOrbital:           label = "Alpha";                   break;
      case BetaOrbital:            label = "Beta";                    break;
      case TotalDensity:           label = "Total Density";           break;
      case SpinDensity:            label = "Spin Density";            break;
      case AlphaDensity:           label = "Alpha Density";           break;
      case BetaDensity:            label = "Beta Density";            break;
      case DensityCombo:           label = "User Defined Density";    break;
      case CubeData:               label = "Cube Data";               break;
      case VanDerWaals:            label = "van der Waals";           break;
      case Promolecule:            label = "Promolecule";             break;
      case SolventExcluded:        label = "Solvent Excluded";        break;
      case SID:                    label = "SID";                     break;
      case ElectrostaticPotential: label = "Electrostatic Potential"; break;
      case Geminal:                label = "Geminal";                 break;
      case Correlation:            label = "Correlated Density";      break;
      case CustomDensity:          label = "Custom Density";          break;
      case BasisFunction:          label = "Basis Function";          break;
      case DysonLeft:              label = "Dyson (left)";            break;
      case DysonRight:             label = "Dyson (right)";           break;
      case MullikenAtomic:         label = "Mulliken Atomic";         break;
      case MullikenDiatomic:       label = "Mulliken Diatomic";       break;
      case GenericOrbital:         label = "Orbital";                 break;
      case Ribbon:                 label = "Ribbon";                  break;

      case AlphaRealOrbital:       label = "Alpha Real Orbital";      break;
      case AlphaImaginaryOrbital:  label = "Alpha Imaginary Orbital"; break;
      case BetaRealOrbital:        label = "Beta Real Orbital";       break;
      case BetaImaginaryOrbital:   label = "Beta Imaginary Orbital";  break;
   }

   if (isIndexed()) label += " " + QString::number(m_index+1);
   return label;
}


QString SurfaceType::toDisplayString() const
{
   // [i18n] 界面显示名 = 数据键的译文。数据键本身保持不变，
   // 以保证 operator==、文件名、图层比较等逻辑不受语言影响。
   //
   // 注意：SurfaceType 继承自 Data::Base（普通 C++ 类，非 QObject），
   // 没有 tr() 可用，必须用 QCoreApplication::translate 并显式指定
   // 上下文 IQmol::Data::SurfaceType。
   QString label(toString());
   QString suffix;
   if (isIndexed() && m_index >= 0) {
      // 先摘掉尾部编号（如 "Alpha 1" 的 " 1"）再翻译，稍后加回
      suffix = " " + QString::number(m_index+1);
      label.chop(suffix.length());
   }

   // 数据键 -> 已翻译显示名。QCoreApplication::translate 用完整上下文取词，
   // 上下文与 translations/zh_CN.ts 中 IQmol::Data::SurfaceType 一致。
   //
   // 每条字面量都显式写出，不用宏拼接 —— lupdate 在宏展开前的源码上
   // 做静态扫描，宏里的 translate() 参数提取不到。
   QString translated;
   if      (label == "Alpha")                   translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Alpha");
   else if (label == "Beta")                    translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Beta");
   else if (label == "Total Density")           translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Total Density");
   else if (label == "Spin Density")            translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Spin Density");
   else if (label == "Alpha Density")           translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Alpha Density");
   else if (label == "Beta Density")            translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Beta Density");
   else if (label == "User Defined Density")    translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "User Defined Density");
   else if (label == "Cube Data")               translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Cube Data");
   else if (label == "van der Waals")           translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "van der Waals");
   else if (label == "Promolecule")             translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Promolecule");
   else if (label == "Solvent Excluded")        translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Solvent Excluded");
   else if (label == "SID")                     translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "SID");
   else if (label == "Electrostatic Potential") translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Electrostatic Potential");
   else if (label == "Geminal")                 translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Geminal");
   else if (label == "Correlated Density")      translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Correlated Density");
   else if (label == "Custom Density")          translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Custom Density");
   else if (label == "Basis Function")          translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Basis Function");
   else if (label == "Dyson (left)")            translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Dyson (left)");
   else if (label == "Dyson (right)")           translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Dyson (right)");
   else if (label == "Mulliken Atomic")         translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Mulliken Atomic");
   else if (label == "Mulliken Diatomic")       translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Mulliken Diatomic");
   else if (label == "Orbital")                 translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Orbital");
   else if (label == "Ribbon")                  translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Ribbon");
   else if (label == "Alpha Real Orbital")      translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Alpha Real Orbital");
   else if (label == "Alpha Imaginary Orbital") translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Alpha Imaginary Orbital");
   else if (label == "Beta Real Orbital")       translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Beta Real Orbital");
   else if (label == "Beta Imaginary Orbital")  translated = QCoreApplication::translate("IQmol::Data::SurfaceType", "Beta Imaginary Orbital");
   else {
      // Custom 类型的 label 是用户/解析器给的名字，原样返回
      return toString();
   }

   return translated + suffix;
}


bool SurfaceType::operator==(SurfaceType const& that) const
{
   bool same(m_kind == that.m_kind && m_index == that.m_index);
   if (m_kind == Custom) same = same && m_label == that.m_label;

   return same;
}


bool SurfaceType::isIndexed() const
{
   return m_kind == AlphaOrbital     ||  m_kind == BetaOrbital           || 
          m_kind == DysonLeft        ||  m_kind == DysonRight            ||
          m_kind == Geminal          ||  m_kind == Correlation           ||
          m_kind == BasisFunction    ||  m_kind == GenericOrbital        ||
          m_kind == AlphaRealOrbital ||  m_kind == AlphaImaginaryOrbital ||
          m_kind == BetaRealOrbital  ||  m_kind == BetaImaginaryOrbital;
}


bool SurfaceType::isOrbital() const
{
   return m_kind == AlphaOrbital          || 
          m_kind == BetaOrbital           ||
          m_kind == DysonLeft             || 
          m_kind == DysonRight            ||
          m_kind == GenericOrbital        ||
          m_kind == AlphaRealOrbital      ||
          m_kind == AlphaImaginaryOrbital ||
          m_kind == BetaRealOrbital       ||
          m_kind == BetaImaginaryOrbital;
}


bool SurfaceType::isBasis() const
{
   return (m_kind == BasisFunction);
}

bool SurfaceType::isDensity() const
{
   return (m_kind == AlphaDensity)   || (m_kind == BetaDensity)      ||
          (m_kind == TotalDensity)   || (m_kind == SpinDensity)      ||
          (m_kind == MullikenAtomic) || (m_kind == MullikenDiatomic) ||
          (m_kind == DensityCombo)   || (m_kind == Correlation)      ||
          (m_kind == CustomDensity);
}


bool SurfaceType::isRegularDensity() const
{
   return (m_kind == AlphaDensity) || (m_kind == BetaDensity) ||
          (m_kind == TotalDensity) || (m_kind == SpinDensity);
}


bool SurfaceType::isSigned() const
{
   return (m_kind == AlphaOrbital)     || (m_kind == BetaOrbital)           ||
          (m_kind == DysonLeft)        || (m_kind == DysonRight)            ||
          (m_kind == SpinDensity)      || (m_kind == DensityCombo)          ||
          (m_kind == MullikenAtomic)   || (m_kind == MullikenDiatomic)      ||
          (m_kind == Geminal)          || (m_kind == Correlation)           ||
          (m_kind == BasisFunction)    || (m_kind == GenericOrbital)        ||
          (m_kind == AlphaRealOrbital) || (m_kind == AlphaImaginaryOrbital) ||
          (m_kind == BetaRealOrbital)  || (m_kind == BetaImaginaryOrbital)  ||
          (m_kind == CustomDensity) ;
}


void SurfaceType::dump() const 
{
   qDebug() << toString();
}

} } // end namespace IQmol::Data
